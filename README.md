# Decentralized Watchtower

This project implements a decentralized Watchtower for CoW’s [Smart Contract Orders](https://blog.cow.fi/tutorial-creating-smart-orders-on-cow-protocol-683a5f9f4763?gi=892db4501ab6) (SCOs) using [Autonolas](https://olas.network/) technology. The SCOs allow autonomous trading based on predefined rules and strategies. The Watchtower monitors the activity of SCOs, registers new contracts, and forwards tradable orders to the CoW Protocol API. 
This implementation intends to strike a balance between decentralization, efficiency, and scalability, contributing to increasingly the autonomy, security, and transparency of the off-chain components for CoW's trading ecosystem.

The project leverages Autonolas technology to implement the Watchtower as a multi-agent system, enabling it to operate efficiently while minimizing the trust assumptions involved with running off-chain architecture. 

More details can be found [here](https://forum.cow.fi/t/grant-application-decentralizing-cow-s-watchtower/1681).

## Developing

- Clone the repository:

      git clone git@github.com:valory-xyz/decentralized-watchtower.git

- System requirements:

    - Python `>=3.7`
    - [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
    - [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
    - [Pipenv](https://pipenv.pypa.io/en/latest/installation/) `>=2021.x.xx`
    - [Docker Engine](https://docs.docker.com/engine/install/)
    - [Docker Compose](https://docs.docker.com/compose/install/)

- Pull pre-built images:

      docker pull valory/composable-cow:latest

- Create development environment:

      make new_env && pipenv shell

- Configure command line:

      autonomy init --reset --author balancer --remote --ipfs --ipfs-node "/dns/registry.autonolas.tech/tcp/443/https"

- Pull packages:

      autonomy packages sync --update-packages

- During development use `make formatters`, `make code-checks` and `make generators`


- After building your development environment and pulling the packages, you can conduct an end-to-end test with a local network and 4 agents by running
      
      pytest packages/valory/agents/decentralized_watchtower/tests/test_agents/test_decentralized_watchtower.py::TestWatchtowerFourAgents

## Healthcheck for the agent

The agents offer an http endpoint. It listens on port 8000. Once you have an agent running, you can check it's health status by calling the /healthcheck endpoint. 
Example:  
```bash
curl http://localhost:8000/healthcheck
```

An example response:
```json
{
      "healthy": true,
      "period": 1,
      "tm_ok": true,
      "web3_ok": true,
}
```

In case of issues with the agent, the "healthy" field will be set to false.
