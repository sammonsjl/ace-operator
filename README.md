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

## Status

Early. Implemented: the CRD, the reconcile order, the gateway init chain, and
sub-CR rendering for all three components.

**Not yet implemented** — `deploy_gateway`, `postgres` and `redis` are
scaffolds. The gateway Deployment, its envoy sidecar and config, the Service
and the Ingress are the next piece of work, and nothing installs end to end
until they exist.
