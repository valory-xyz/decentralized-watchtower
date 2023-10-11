# Decentralized Watchtower Kubernetes deployments

This folder contains sample Kubernetes deployments for four agents and their corresponding Tendermint nodes.

> **:warning: Warning** <br />
> **Please note that the keys used in this folder (as well as any confidential value or API key) are dummy values for demonstration purposes only, and they need to be instantiated with your own values. Never use the keys provided in this folder in a production environment.**
>

The following guide assumes that you have a running Kubernetes cluster and that the KUBECONFIG environment variable is correctly pointing to the Kubernetes configuration file.

We provide template Kubernetes deployments using a sample Ethereum `keys.json` file (randomly generated):

```json
[
  {
    "address": "0xCAF30F32e34482e3818C95B9C40702e77D879dBf",
    "private_key": "0xc5b34c07c92a7f3f57e3c4a6dc9625706c19291f161fa98f5cc55fa701852b45"
  },
  {
    "address": "0x3b3964b4b2C92aB3ca2Af5EBfF08c32B0A2B1A6A",
    "private_key": "0x99fdaf57ee6e7cc270a61e9491ee5d81385d9b32fd38a73e9a358fc0c9d5f577"
  },
  {
    "address": "0x4C04db92F3d7F9F78a344D4C6f80250d3e6f4cA6",
    "private_key": "0x846de4f71f73055ff934fcdf32b218e628823c7253e807bcd81e7488b68165ca"
  },
  {
    "address": "0x9B4205930F4bF6a0D402F1068279f5A57fC346Fb",
    "private_key": "0x037a823b7d4e4ecc81b88862f5836b4852b4ac4e10ea03b6b9bea4d1b8922e33"
  }
]
```

You can find these deployments in the folders

- `./abci_build_goerli`,
- `./abci_build_ethereum`, and
- `./abci_build_gnosis`.

You can either edit the required parameters directly in the Kubernetes YAML files (agent addresses, agent keys, Safe address, HTTP RPC, and WS RPC), or re-create the YAML using the instructions below.

## Re-create the Kubernetes deployments

### Görli deployment

```bash
# Replace with your agents' addresses
export ALL_PARTICIPANTS='["0x4C04db92F3d7F9F78a344D4C6f80250d3e6f4cA6", "0xCAF30F32e34482e3818C95B9C40702e77D879dBf", "0x9B4205930F4bF6a0D402F1068279f5A57fC346Fb", "0x3b3964b4b2C92aB3ca2Af5EBfF08c32B0A2B1A6A"]'

# Replace with your service Gnosis Safe
export SAFE_CONTRACT_ADDRESS=0x5000000000000000000000000000000000000000
export USE_ACN=false
export COW_API_URL=https://api.cow.fi/goerli/api/v1
export SERVICE_REGISTRY_ADDRESS=0x9c7d6D8D6c11e5F146628fd8478f73FAcc10C6B3
export ON_CHAIN_SERVICE_ID=53
export CHAIN_ID=5
export HTTP_RPC=YOUR_HTTP_RPC
export WS_RPC=YOUR_WS_RPC

autonomy init --remote --author open_operator --reset

# The fetch hash can be obtained from `packages.json`.
# Ensure that you are fetching the hash corresponding to the version you want to deploy.
autonomy fetch bafybeihfusu3so7k6ksp36tqm6w2ss5uyz76u4u2vh62rsjpdnjsy5z4y4 --service
cd decentralized_watchtower_goerli

# Use your own keys.json file
cp ../keys.json .
autonomy deploy build --kubernetes -ltm --image-author valory
cd abci_build

# The Kubernetes deployment YAML files are located in the /abci_build folder
```

### Ethereum deployment

```bash
# Replace with your agents' addresses
export ALL_PARTICIPANTS='["0x4C04db92F3d7F9F78a344D4C6f80250d3e6f4cA6", "0xCAF30F32e34482e3818C95B9C40702e77D879dBf", "0x9B4205930F4bF6a0D402F1068279f5A57fC346Fb", "0x3b3964b4b2C92aB3ca2Af5EBfF08c32B0A2B1A6A"]'

# Replace with your service Gnosis Safe
export SAFE_CONTRACT_ADDRESS=0xcD1C69fC6066036D0216E8479F2ca8F7019BD910
export USE_ACN=true
export COW_API_URL=https://api.cow.fi/mainnet/api/v1
export SERVICE_REGISTRY_ADDRESS=0x48b6af7B12C71f09e2fC8aF4855De4Ff54e775cA
export ON_CHAIN_SERVICE_ID=7
export CHAIN_ID=1
export HTTP_RPC=YOUR_HTTP_RPC
export WS_RPC=YOUR_WS_RPC

autonomy init --remote --author open_operator --reset

# The fetch hash can be obtained from `packages.json`.
# Ensure that you are fetching the hash corresponding to the version you want to deploy.
autonomy fetch bafybeibmi7ap625qg7hea52nysxqllmlqpleu4loks5mnnof63b4pmmjem --service
cd decentralized_watchtower

# Use your own keys.json file
cp ../keys.json .
autonomy deploy build --kubernetes -ltm --image-author valory
cd abci_build

# The Kubernetes deployment YAML files are located in the /abci_build folder
```

### Gnosis deployment

```bash
# Replace with your agents' addresses
export ALL_PARTICIPANTS='["0x4C04db92F3d7F9F78a344D4C6f80250d3e6f4cA6", "0xCAF30F32e34482e3818C95B9C40702e77D879dBf", "0x9B4205930F4bF6a0D402F1068279f5A57fC346Fb", "0x3b3964b4b2C92aB3ca2Af5EBfF08c32B0A2B1A6A"]'

# Replace with your service Gnosis Safe
export SAFE_CONTRACT_ADDRESS=0xb407Ba7Fa8844de0CA0B7fE40Ae6fCbbf8900309
export USE_ACN=true
export COW_API_URL=https://api.cow.fi/gnosis/api/v1
export SERVICE_REGISTRY_ADDRESS=0x9338b5153AE39BB89f50468E608eD9d764B755fD
export ON_CHAIN_SERVICE_ID=8
export CHAIN_ID=100
export HTTP_RPC=YOUR_HTTP_RPC
export WS_RPC=YOUR_WS_RPC

autonomy init --remote --author open_operator --reset

# The fetch hash can be obtained from `packages.json`.
# Ensure that you are fetching the hash corresponding to the version you want to deploy.
autonomy fetch bafybeifpzq6tejipr75fgea5zt67cqjoe2ugps545rqcb53uike7vc2eba --service
cd decentralized_watchtower_gnosis

# Use your own keys.json file
cp ../keys.json .
autonomy deploy build --kubernetes -ltm --image-author valory
cd abci_build

# The Kubernetes deployment YAML files are located in the /abci_build folder
```

## Deploying

After configuring the deployment to align with your specific parameters and keys, you are ready to initiate the deployment process using `kubectl`.

The provided deployment templates make use of `persistentVolumeClaim`s, which require the provision of a corresponding `StorageClass` for the deployment. To begin, navigate to the directory containing the deployment files for the desired blockchain network you intend to deploy. From there, generate a file named `storageclass.yaml`.

Below is an illustrative instance tailored for AWS EFS. Keep in mind that you should adapt the `StorageClass` definition to match the specific `StorageClass` required by your cluster:

```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: nfs-ephemeral
provisioner: efs.csi.aws.com
mountOptions:
  - tls
  - iam
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-00000000000000000
  directoryPerms: "700"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
  basePath: "/"
```

Having configured the `StorageClass`, you can now proceed to deploy to your cluster by executing the following command in your terminal:

```bash
kubectl apply --recursive -f .
```

This command initiates the deployment process, recursively applying the necessary configurations from the current directory and its subdirectories.

## Source code updates

This section summarizes the process of implementing code updates on the service and so that it can be used within a Kubernetes cluster. The information contained in this section is an excerpt of the [Open Autonomy - Guides](https://docs.autonolas.network/open-autonomy/guides/).

The goal is to generate and publish the **Docker image** and the **Kubernetes configuration files** reflecting the change in the code base of the service.

1. Clone, prepare your repository and Pipenv environment as described in the section [Developing](../README.md#developing) in the main README.md of this repository. Follow the recommendations therein when updating the code base (usage of code formatters, testing, etc.).

2. Once you are happy and have tested locally the changes in the code base, lock and push your packages:

    ```bash
    autonomy packages lock
    autonomy push-all
    ```

3. Fetch the service you are interested in updating. We will be using the Görli variant as an example.

    ```bash
    autonomy fetch valory/decentralized_watchtower_goerli --service --local
    cd decentralized_watchtower_goerli
    ```

4. Build the Docker image. You must use your Docker Hub user name as `--image-author`. We use `valory` as an example:

    ```bash
    autonomy build-image --image-author valory
    ```

    The output should look similar to this:

    ```bash
    [docker]Successfully tagged valory/oar-decentralized_watchtower:<hash>
    ```

5. Publish the Docker image to your Docker Hub account use the `<hash>` value from the step above.

    ```bash
    docker login -u valory -p <password>
    docker push valory/oar-decentralized_watchtower:<hash>
    docker logout
    ```

    Ensure that the image is publicly available.

6. Re-create the Kubernetes deployment defining the appropriate environment variables as [specified above](#re-create-the-kubernetes-deployments). Note that you can skip init the framework and fetching the service, because these steps have been done in steps 1-3 above. Ensure that `--image-author` matches your Docker Hub name in the command `autonomy deploy build` (this is to reference the correct Docker Hub user and image name in the generated deployment). Here is an example for Göerli and image author `valory`:

    ```bash
    # Replace with your agents' addresses
    export ALL_PARTICIPANTS='["0x4C04db92F3d7F9F78a344D4C6f80250d3e6f4cA6", "0xCAF30F32e34482e3818C95B9C40702e77D879dBf", "0x9B4205930F4bF6a0D402F1068279f5A57fC346Fb", "0x3b3964b4b2C92aB3ca2Af5EBfF08c32B0A2B1A6A"]'

    # Replace with your service Gnosis Safe
    export SAFE_CONTRACT_ADDRESS=0x5000000000000000000000000000000000000000
    export USE_ACN=false
    export COW_API_URL=https://api.cow.fi/goerli/api/v1
    export SERVICE_REGISTRY_ADDRESS=0x9c7d6D8D6c11e5F146628fd8478f73FAcc10C6B3
    export ON_CHAIN_SERVICE_ID=53
    export CHAIN_ID=5
    export HTTP_RPC=YOUR_HTTP_RPC
    export WS_RPC=YOUR_WS_RPC

    # Use your own keys.json file
    cp ../keys.json .
    autonomy deploy build --kubernetes -ltm --image-author valory
    cd abci_build
    # The Kubernetes deployment YAML files are located in the /abci_build folder
    ```

## References

- [Autonolas Developer Documentation - Open Autonomy framework](https://docs.autonolas.network/open-autonomy/)
- [Autonolas Developer Documentation - Deploy the service](https://docs.autonolas.network/open-autonomy/guides/deploy_service/)
- [Open Operator - Decentralized Watchtower Service](https://github.com/valory-xyz/open-operator-watchtower)
