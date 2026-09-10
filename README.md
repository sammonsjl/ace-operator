# ace-operator

Deploys **ACE** — an open-source, upstream-built automation platform — to
Kubernetes, from a single `AutomationPlatform` custom resource.

```yaml
apiVersion: automation.ace.io/v1alpha1
kind: AutomationPlatform
metadata:
  name: ace
spec:
  gateway:
    external_url: https://ace.example.com
```

Every image it deploys is built from upstream source by
[ace-images](https://github.com/sammonsjl/ace-images) and published to GHCR.
Nothing comes from a vendor registry. See [`NOTICE`](NOTICE).

## How it works

An Ansible-based Operator SDK operator. `watches.yaml` maps
`AutomationPlatform` to `playbooks/platform.yml`, which runs seven roles in a
deliberate order:

| Role | What it does |
|---|---|
| `common` | Resolves images and secrets, decides which components are enabled |
| `redis` / `postgres` | The two stateful dependencies |
| `deploy_gateway` | The gateway Deployment, envoy, Service, Ingress |
| `initialize_gateway` | The `aap-gateway-manage` init chain, inside the pod |
| `deploy_components` | Renders a sub-CR per component |
| `post_install` | Waits for readiness, then merges service data |

**The order is the whole design.** `initialize_gateway` ends by generating a
service secret per component; those secrets are what each component's
resource-server settings are built from. Deploying a component before its
secret exists produces a platform that looks healthy and fails every login —
the classic JWT-handshake failure. So components are never deployed until the
gateway has issued their secrets, and service data is never merged until the
components answer.

## It drives other operators, and does not replace them

`deploy_components` renders one CR per component and lets that component's own
operator reconcile it:

| Component | CR | Operator | Licence |
|---|---|---|---|
| controller | `AWX` | [awx-operator](https://github.com/ansible/awx-operator) | Apache-2.0 |
| hub | `Galaxy` | [galaxy-operator](https://github.com/ansible/galaxy-operator) | GPLv2+ |
| EDA | `EDA` | [eda-server-operator](https://github.com/ansible/eda-server-operator) | Apache-2.0 |

All three must be installed in the cluster. That is a real dependency, and it
is deliberate: awx-operator is the largest and best-tested piece of this stack,
and forking it to save one install would be the wrong trade.

Creating those operators' custom resources is ordinary API use. **No code is
copied from them** — for the GPLv2+ ones that would conflict with this repo's
Apache-2.0 licence.

Each sub-CR sets `image` and `image_version` explicitly, so the components run
ACE's images rather than the operators' upstream defaults. That is the single
check worth running after an install:

```bash
kubectl get pods -A -o jsonpath='{..image}' | tr ' ' '\n' | sort -u | grep ace-
```

## The gateway pod

The gateway is the only component this operator deploys itself, and its pod is
two containers: the gateway and **envoy**, sharing a network namespace.

That sharing is the point. On a podman host the two run with `network: host`
and reach each other on `127.0.0.1`; in a pod they get the identical wiring
without needing the host's network. Envoy holds almost no static config — its
listeners and clusters arrive over xDS from the gateway's gRPC control plane,
so a route exists because a component registered itself, not because it was
written into a file.

Migrations run in an **init container**, and the long-running container only
supervises processes. That is the vendor's own split, and it is what makes the
Deployment safe to restart: nothing in the main container mutates the schema.

## Status

Implemented: the CRD, the reconcile order, postgres and redis, the gateway
(ConfigMaps, Deployment, envoy sidecar, Service), the `aap-gateway-manage` init
chain, sub-CR rendering for all three components, and `migrate_service_data`.

### Known gap: service registration must come first

`initialize_gateway` currently calls `generate_service_secret` before anything
has been registered with the gateway, and the gateway rejects it:

    argument api-slug: invalid choice: 'controller' (choose from )

The choice list is empty because no service exists yet. The containerized
installer gets this right and shows the order:

1. set the gateway proxy URL setting
2. create the API http port
3. **register each service** — service type, cluster, node, then the route
4. verify the gateway answers through envoy
5. *then* `generate_service_secret` per component

So a `register_services` step belongs between `initialize_gateway` and
`deploy_components`, driving the gateway's REST API the way
`roles/automationgateway/tasks/postinstall.yml` does in
[ace-containerized-installer](https://github.com/sammonsjl/ace-containerized-installer).
Until it exists, the reconcile gets as far as a working gateway and stops.

Also not done: an Ingress (the Service is reachable, but nothing terminates a
real hostname), backup/restore kinds, and a molecule suite.
