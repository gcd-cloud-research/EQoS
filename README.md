# eHQoS

## Authors

* Pere Piñol Pueyo <perepinol@gmail.com>
* Supervisors:
  * Jordi Mateo Fornés <jordi.mateo@udl.cat>, @github/JordiMateoUdL
  * Francesc Solsona Tehàs <francesc.solsona@udl.cat>

## About

The repository contains all code related to an eHQoS implementation.

* _images_: Contains all the services used in the implementation, grouped so that building them is easier.
* _kubernetes_: .yaml files to deploy the services in a Kubernetes cluster.
* _obsolete_: Files that are no longer needed, but are included because they may clarify some aspects of the implementation.
* _test-routines_: Files that were submitted as routines to test the implementation's performance.
* _utils_: Scripts that may be useful to manage the cluster.

## Using the utils

Start by loading the aliases from the base directory of the repository:

```
$ . ./utils/aliases.sh
```

This initialises several variables that are useful for the rest of the scripts. Afterwards, you can run:

* buildimages.sh [registry search]
    
    Builds the images in the image folder (IMAGE\_DIR). If _registry_ is specified, it pushes the images there and cleans with _prune_. If _search_ is specified, it builds image with directory name _search_, if it exists.

* buildredeploy.sh deployment\_name [image_name]
    
    If _image\_name_ is not provided, it builds the image with directory name _deployment\_name_, then deletes and creates the Kubernetes Deployment associated with it. Otherwise, the image build is specified by _image\_name_, but the deployment reset is the same as in the other case. This is to allow redeployment of Deployments with more than one container in them.

* deployall.sh
    
    Creates all architecture-related Services and Deployments in the Kubernetes cluster.

* kubepod.sh {logs|exec} {pod_name} [logs or exec args]
    
    Runs kubectl logs or kubectl exec given a _pod\_name_ that does not need to be the complete name of a pod. It is necessary for the _pod\_name_ to identify a pod unequivocally.

* redep.sh {deployment_name}
    
    Deletes and creates the deployment with name _deployment\_name_.
