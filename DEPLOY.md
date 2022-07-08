## Deployment

This app is deployed using a combination of technologies.

* [Argo workflows](https://argoproj.github.io/argo-workflows/) is used to run the tasks required to create the app.
* [Kubernetes](https://kubernetes.io/), [Docker](https://www.docker.com/), [Helm](https://helm.sh/) and [minikube](https://minikube.sigs.k8s.io/docs/) are used to orchestrate and deploy the app.
* The code is written in [Python](https://www.python.org/) and makes use of [postcodes.io](https://postcodes.io/), [openstreetmap](https://www.openstreetmap.org/) and [mpld3](https://mpld3.github.io/).


```
cd argo-workflows

# Setup Minikube
minikube start
minikube node add

# Build image
cd docker/python-image
docker build . -t python-image:latest
minikube image load python-image:latest
cd ../../

# Get ARGO and start Argo
helm repo add argo https://argoproj.github.io/argo-helm
cd helm
helm install argo argo/argo-workflows -n argo --values values.yaml --create-namespace --version 0.16.6
kubectl describe deployment -n argo
cd ..

# Apply remaining kubernetes resources
kubectl apply -f kubernetes/

# In a new terminal, port forward argo
kubectl -n argo port-forward svc/argo-workflows-server 2746:2746

# Submit a workflow
export ARGO_NAMESPACE=argo
argo submit workflows/create-interactive-map

```
Then navigate to `localhost:2746`


