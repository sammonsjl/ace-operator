# The operator image: the Ansible Operator base plus this repo's reconcile logic.
FROM quay.io/operator-framework/ansible-operator:v1.37.0

USER root
RUN dnf -y install python3-pip && dnf clean all
USER 1001

COPY requirements.yml ${HOME}/requirements.yml
RUN ansible-galaxy collection install -r ${HOME}/requirements.yml \
 && chmod -R ug+rwx ${HOME}/.ansible

COPY watches.yaml ${HOME}/watches.yaml
COPY roles/        ${HOME}/roles/
COPY playbooks/    ${HOME}/playbooks/
