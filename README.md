# Hands-on Kubernetes-01 : Installing Kubernetes on Ubuntu running on AWS EC2 Instances

Purpose of the this hands-on training is to give students the knowledge of how to install and configure Kubernetes on Ubuntu EC2 Instances.

## Learning Outcomes

At the end of the this hands-on training, students will be able to;

- install Kubernetes on Ubuntu.

- explain steps of the Kubernetes installation.

- set up a Kubernetes cluster.

- explain the Kubernetes architecture.

- deploy a simple server on Kubernetes cluster.

## Outline

- Part 1 - Setting Up Kubernetes Environment on All Nodes

- Part 2 - Setting Up Master Node for Kubernetes

- Part 3 - Adding the Slave/Worker Nodes to the Cluster

- Part 4 - Deploying a Simple Nginx Server on Kubernetes

- Part 5 - Deploying a Simple Nginx Server on Kubernetes


## Part 1 - Setting Up Kubernetes Environment on All Nodes

- In this hands-on, we will prepare two nodes for Kubernetes on `Ubuntu 22.04`. One of the node will be configured as the Master node, the other will be the worker node. Following steps should be executed on all nodes. *Note: It is recommended to install Kubernetes on machines with `2 CPU Core` and `2GB RAM` at minimum to get it working efficiently. For this reason, we will select `m7i-flex.large` as EC2 instance type, which has `2 CPU Core` and `8 GB RAM`.*

- Explain briefly [required ports](https://kubernetes.io/docs/reference/networking/ports-and-protocols/)  for Kubernetes. 

- Create two security groups. Name the first security group as master-sec-group and apply the following Control-plane (Master) Node(s) table to your master node.

- Name the second security group as worker-sec-group, and apply the following Worker Node(s) table to your worker nodes.

### Control-plane (Master) Node(s)

|Protocol|Direction|Port Range|Purpose|Used By|
|---|---|---|---|---|
|TCP|Inbound|6443|Kubernetes API server|All|
|TCP|Inbound|2379-2380|`etcd` server client API|kube-apiserver, etcd|
|TCP|Inbound|10250|Kubelet API|Self, Control plane|
|TCP|Inbound|10259|kube-scheduler|Self|
|TCP|Inbound|10257|kube-controller-manager|Self|
|TCP|Inbound|22|remote access with ssh|Self|
|UDP|Inbound|8472|Cluster-Wide Network Comm. - Flannel VXLAN|Self|

### Worker Node(s)

|Protocol|Direction|Port Range|Purpose|Used By|
|---|---|---|---|---|
|TCP|Inbound|10250|Kubelet API|Self, Control plane|
|TCP|Inbound|10256|kube-proxy|Self, Load balancers|
|TCP|Inbound|30000-32767|NodePort Services|All|
|TCP|Inbound|22|remote access with ssh|Self|
|UDP|Inbound|8472|Cluster-Wide Network Comm. - Flannel VXLAN|Self|

> **Ignore this section for AWS instances. But, it must be applied for real servers/workstations.**
>
> - Find the line in `/etc/fstab` referring to swap, and comment out it as following.
>
> ```bash
> # Swap a usb extern (3.7 GB):
> #/dev/sdb1 none swap sw 0 0
>```
>
> or,
>
> - Disable swap from command line
>
> ```bash
> free -m
> sudo swapoff -a && sudo sed -i '/ swap / s/^/#/' /etc/fstab
> ```
>

- Hostname change of the nodes, so we can discern the roles of each nodes. For example, you can name the nodes (instances) like `kube-master, kube-worker-1`

```bash
sudo hostnamectl set-hostname <node-name-master-or-worker>
bash
```

### Install Container Runtimes

- We install required container runtimes according to [`kubernetes Container Runtimes`] (https://kubernetes.io/docs/setup/production-environment/container-runtimes/) documentation.

#### Install and configure prerequisites - v1 - eski doküman (Flannel için hala geçerli sayabiliriz)

- Not: Kubernetes ekibinin dokümantasyonu basitleştirme ve sorumluluğu "Container Network Interface" (CNI) dediğimiz (Flannel, Calico, Cilium gibi) ağ eklentilerine devretme stratejisinin bir parçası. Özetle; eski yöntem "her şeyi baştan garantiye alalım" diyordu, yeni yöntem ise "sadece en temel olanı (IP Forwarding) yapalım, gerisini kullandığın ağ çözümü halletsin" diyor.

- Forwarding IPv4 and letting iptables see bridged traffic:

```bash
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# sysctl params required by setup, params persist across reboots
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

# Apply sysctl params without reboot
sudo sysctl --system
```

- Verify that the br_netfilter, overlay modules are loaded by running the following commands:

```bash
lsmod | grep br_netfilter
lsmod | grep overlay
```

- Verify that the net.bridge.bridge-nf-call-iptables, net.bridge.bridge-nf-call-ip6tables, and net.ipv4.ip_forward system variables are set to 1 in your sysctl config by running the following command:

```bash
sysctl net.bridge.bridge-nf-call-iptables net.bridge.bridge-nf-call-ip6tables net.ipv4.ip_forward
```


#### Install and configure prerequisites - v2 - güncel doküman

```bash
#Enable IPv4 packet forwarding
#To manually enable IPv4 packet forwarding:

# sysctl params required by setup, params persist across reboots
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.ipv4.ip_forward = 1
EOF

# Apply sysctl params without reboot
sudo sysctl --system

#Verify that net.ipv4.ip_forward is set to 1 with:
sysctl net.ipv4.ip_forward

```


#### Install containerd on ubuntu (https://docs.docker.com/engine/install/ubuntu/)

- Set up Docker's apt repository.

```bash
# Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
```

- Install containerd.

```bash
sudo apt-get install containerd.io
```

- Check the containerd.

```bash
sudo systemctl status containerd
```

- Test the containerd.

```bash
sudo ctr images pull docker.io/library/redis:alpine
sudo ctr run -d docker.io/library/redis:alpine redis
sudo ctr container ls
```

#### Install nerdctl (Optional)

- While the ctr tool is bundled together with containerd, it should be noted the ctr tool is solely made for debugging containerd. The nerdctl tool provides stable and human-friendly user experience.

- Download the nerdctl binary from nerdctl github page. (https://github.com/containerd/nerdctl/releases)

- Download `nerdctl-full-*-linux-amd64.tar.gz` release.

```bash
wget https://github.com/containerd/nerdctl/releases/download/v1.7.6/nerdctl-full-1.7.6-linux-amd64.tar.gz
```

- Extract the archive to a path like `/usr/local`.

```bash
sudo tar xvf nerdctl-full-1.7.6-linux-amd64.tar.gz -C /usr/local
```

- Test the `nerdctl`.

```bash
sudo nerdctl run -d --name redis redis:alpine
sudo nerdctl container ls
```

#### cgroup drivers (https://kubernetes.io/docs/setup/production-environment/container-runtimes/)

- On Linux, control groups are used to constrain resources that are allocated to processes.

- Both the kubelet and the underlying container runtime need to interface with control groups to enforce resource management for pods and containers and set resources such as cpu/memory requests and limits. To interface with control groups, the kubelet and the container runtime need to use a cgroup driver. `It's critical that the kubelet and the container runtime use the same cgroup driver and are configured the same`.

- There are two cgroup drivers available:

  cgroupfs
  systemd

#### Configuring the systemd cgroup driver for containerd.

- Configure containerd so that it starts using systemd as cgroup.

```bash
sudo containerd config default | sudo tee /etc/containerd/config.toml >/dev/null 2>&1
sudo sed -i 's/SystemdCgroup \= false/SystemdCgroup \= true/g' /etc/containerd/config.toml
```

Restart and enable containerd service

```bash
sudo systemctl restart containerd
sudo systemctl enable containerd
```

### Install kubeadm (https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/)

### Version skews

- Kubernetes version and version-skew policy (https://kubernetes.io/releases/version-skew-policy/)
- Kubeadm-specific version skew policy (https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/#version-skew-policy)


### Install helper packages for Kubernetes. ( Kubernetes version: v1.34 - daha sonrasında upgrade yapmak için bir düşük versiyonu yüklüyorum.)

```bash
# 1- Update the apt package index and install packages needed to use the Kubernetes apt repository:
sudo apt-get update

# apt-transport-https may be a dummy package; if so, you can skip that package
sudo apt-get install -y apt-transport-https ca-certificates curl gpg


# 2- Download the public signing key for the Kubernetes package repositories. The same signing key is used for all repositories so you can disregard the version in the URL:

# If the directory `/etc/apt/keyrings` does not exist, it should be created before the curl command, read the note below.
#sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.34/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg


# 3- Add the Kubernetes apt repository:
# This overwrites any existing configuration in /etc/apt/sources.list.d/kubernetes.list
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.34/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list


# 4- Update the apt package index, install kubelet, kubeadm and kubectl, and pin their version:
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

# 5- Enable the kubelet service before running kubeadm: (Optional)
sudo systemctl enable --now kubelet

```


## Part 2 - Setting Up Master Node for Kubernetes (https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)

- Following commands should be executed on Master Node only.

- Pull the packages for Kubernetes beforehand

```bash
sudo kubeadm config images pull
```

- Let `kubeadm` prepare the environment for you. Note: Do not forget to change `<ec2-private-ip>` with your master node private IP.


```bash
# --pod-network-cidr=10.244.0.0/16 önemli flannel kullanacaksan (10.244.0.0/16) - Ancak calico kullanacaksan (192.168.0.0/16)
sudo kubeadm init --apiserver-advertise-address=<ec2-private-ip> --pod-network-cidr=10.244.0.0/16
sudo kubeadm init --apiserver-advertise-address=10.8.2.127 --pod-network-cidr=192.168.0.0/16

echo "10.8.2.127 k8s-master-nlb-042169c453dd877f.elb.us-east-1.amazonaws.com" | sudo tee -a /etc/hosts


sudo kubeadm init \
  --apiserver-advertise-address=10.8.2.127 \
  --control-plane-endpoint="k8s-master-nlb-042169c453dd877f.elb.us-east-1.amazonaws.com:6443" \
  --pod-network-cidr=192.168.0.0/16 \
  --upload-certs



sudo kubeadm reset -f
sudo rm -rf $HOME/.kube
sudo rm -rf /etc/kubernetes/
sudo rm -rf /var/lib/etcd



```

> :warning: **Note**: If you are working on `t2.micro` or `t2.small` instances,  use the command with `--ignore-preflight-errors=NumCPU` as shown below to ignore the errors.

>```bash
>sudo kubeadm init --apiserver-advertise-address=<ec2 private ip> --pod-network-cidr=10.244.0.0/16 --ignore-preflight-errors=NumCPU
>```

> **Note**: There are a bunch of pod network providers and some of them use pre-defined `--pod-network-cidr` block. Check the documentation at the References part. We will use Flannel for pod network and Flannel uses 10.244.0.0/16 CIDR block. 

>- In case of problems, use following command to reset the initialization and restart from Part 2 (Setting Up Master Node for Kubernetes).

>```bash
>sudo kubeadm reset
>```

- After successful initialization, you should see something similar to the following output (shortened version).

```bash
...
Your Kubernetes control-plane has initialized successfully!

To start using your cluster, you need to run the following as a regular user:

  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config

Alternatively, if you are the root user, you can run:

  export KUBECONFIG=/etc/kubernetes/admin.conf

You should now deploy a pod network to the cluster.
Run "kubectl apply -f [podnetwork].yaml" with one of the options listed at:
  https://kubernetes.io/docs/concepts/cluster-administration/addons/

Then you can join any number of worker nodes by running the following on each as root:

kubeadm join 172.31.32.92:6443 --token 6grb8s.6jjyof8xi8vtxztb \
        --discovery-token-ca-cert-hash sha256:32d1c906fddc50a865b533f909377b2219ef650373ca1b7d4310de025817a00b
```

> Note down the `kubeadm join ...` part in order to connect your worker nodes to the master node. Remember to run this command with `sudo`.

- Run following commands to set up local `kubeconfig` on master node.

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```


```bash
kubectl -n calico-system set env daemonset/calico-node FELIX_AWSSRCDSTCHECK=Disable
kubectl -n kube-system set env daemonset/calico-node FELIX_AWSSRCDSTCHECK=Disable
```

- Calico AWS: https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-public-cloud/aws
- Calico OnPrem: https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-onprem/onpremises
- Calico video: https://www.youtube.com/watch?v=7LRtytR6ZbA

- Activate the `Flannel` pod networking and explain briefly the about network add-ons on `https://kubernetes.io/docs/concepts/cluster-administration/addons/`.

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

- Master node (also named as Control Plane) should be ready, show existing pods created by user. Since we haven't created any pods, list should be empty.

```bash
kubectl get nodes
```

- Show the list of the pods created for Kubernetes service itself. Note that pods of Kubernetes service are running on the master node.

```bash
kubectl get pods -n kube-system
```

- Show the details of pods in `kube-system` namespace. Note that pods of Kubernetes service are running on the master node.

```bash
kubectl get pods -n kube-system -o wide
```

- We can also see containers with `nerdctl` command.

```bash
sudo nerdctl --namespace k8s.io ps -a
```

- Get the services available. Since we haven't created any services yet, we should see only Kubernetes service.

```bash
kubectl get services
```
## Part 3 - Adding the Worker Nodes to the Cluster

- Show the list of nodes. Since we haven't added worker nodes to the cluster, we should see only master node itself on the list.

```bash
kubectl get nodes
```

- Get the kubeadm `join command` on `master node`.

```bash
kubeadm token create --print-join-command
```

- Run `sudo kubeadm join...` command to have them join the cluster on `worker node`.

```bash
sudo kubeadm join 172.31.3.109:6443 --token 1aiej0.kf0t4on7c7bm2hpa \
    --discovery-token-ca-cert-hash sha256:0e2abfb56733665c0e6204217fef34be2a4f3c4b8d1ea44dff85666ddf722c02
```

- Go to the master node. Get the list of nodes. Now, we should see the new worker nodes in the list.

```bash
kubectl get nodes
```

- Get the details of the nodes.

```bash
kubectl get nodes -o wide
```

## Part 4 - Deploying a Simple Nginx Server on Kubernetes

- Check the readiness of nodes at the cluster on master node.

```bash
kubectl get nodes
```

- Show the list of existing pods in default namespace on master. Since we haven't created any pods, list should be empty.

```bash
kubectl get pods
```

- Get the details of pods in all namespaces on master. Note that pods of Kubernetes service are running on the master node and also additional pods are running on the worker nodes to provide communication and management for Kubernetes service.

```bash
kubectl get pods -o wide --all-namespaces
```

- Create and run a simple `Nginx` Server image.

```bash
kubectl run nginx-server --image=nginx  --port=80
```

- Get the list of pods in default namespace on master and check the status and readyness of `nginx-server`

```bash
kubectl get pods -o wide
```

- Expose the nginx-server pod as a new Kubernetes service on master.

```bash
kubectl expose pod nginx-server --port=80 --type=NodePort
```

- Get the list of services and show the newly created service of `nginx-server`

```bash
kubectl get service -o wide
```

- You will get an output like this.

```text
kubernetes     ClusterIP   10.96.0.1       <none>        443/TCP        13m    <none>
nginx-server   NodePort    10.110.144.60   <none>        80:32276/TCP   113s   run=nginx-server
```

- Open a browser and check the `public ip:<NodePort>` of worker node to see Nginx Server is running. In this example, NodePort is 32276.

- Clean the service and pod from the cluster.

```bash
kubectl delete service nginx-server
kubectl delete pods nginx-server
```

- Check there is no pod left in default namespace.

```bash
kubectl get pods
```

### Delete a worker node from Cluster

- To delete a worker node from the cluster, follow the below steps.

  - Drain and delete worker node on the master.

  ```bash
  kubectl get nodes
  kubectl cordon kube-worker
  kubectl drain kube-worker --ignore-daemonsets --delete-emptydir-data

  kubectl delete node kube-worker
  ```

  - Remove and reset settings on the worker node.

  ```bash
  sudo kubeadm reset
  ```
  
> Note: If you try to have worker rejoin cluster, it might be necessary to clean `kubelet.conf` and `ca.crt` files and free the port `10250`, before rejoining.
>
> ```bash
>  sudo rm /etc/kubernetes/kubelet.conf
>  sudo rm /etc/kubernetes/pki/ca.crt
>  sudo netstat -lnp | grep 10250
>  sudo kill <process-id>
>  ```


# References

- https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/

- https://kubernetes.io/docs/concepts/cluster-administration/addons/

- https://kubernetes.io/docs/reference/

- https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#-strong-getting-started-strong-
# test-app
# test-app
