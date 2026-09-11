# ace

Installs the ACE operator, and optionally a platform for it to reconcile.

## What it installs

- The `AutomationPlatform` CRD, the operator's RBAC, and the operator itself.
- **awx-operator**, as a chart dependency, which reconciles the `AWX` resource
  ACE renders for its controller.
- Optionally an `AutomationPlatform` resource (`platform.create=true`).

## What it does not install

`galaxy-operator` and `eda-server-operator` are **not** dependencies, because
neither publishes a Helm chart -- both ship kustomize bases. They are also
GPLv2+, while this chart is Apache-2.0: creating their custom resources is
ordinary API use and carries no licence obligation, but vendoring their
manifests here would not be so simple.

Install them separately before enabling `platform.hub` or `platform.eda`:

```sh
kubectl apply -k https://github.com/ansible/galaxy-operator/config/default?ref=2024.5.8
kubectl apply -k https://github.com/ansible/eda-server-operator/config/default?ref=1.0.2
```

Both watch only their own namespace, so they must be installed into whichever
namespace the platform lives in.

## Usage

```sh
helm dependency build charts/ace
helm install ace charts/ace -n ace-system --create-namespace
```

With a platform, reachable on its own address:

```sh
helm install ace charts/ace -n ace-system --create-namespace \
  --set platform.create=true \
  --set platform.namespace=ace \
  --set platform.gateway.external_url=https://ace.example.com \
  --set platform.gateway.service_type=LoadBalancer
```

envoy terminates TLS on 443 itself and its listener is programmed by the
gateway over xDS, so `LoadBalancer` gives the front door a real address rather
than putting an HTTP proxy in front of it. Reaching the gateway's plain nginx
port instead serves the console and 404s every component API, because envoy is
what routes `/api/controller/`, `/api/galaxy/` and `/api/eda/`.

## Upgrades

The CRD ships in `crds/`, which Helm installs once and never updates. After a
chart upgrade that changes the schema, apply it by hand:

```sh
kubectl apply -f charts/ace/crds/
```
