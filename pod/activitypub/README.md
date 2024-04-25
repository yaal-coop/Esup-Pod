# ActivityPub implementation

Pod implements a minimal set of ActivityPub that allows video sharing between Pod instances.
The ActivityPub implementation is also compatible with Peertube.

## Federation

Here is what happens when two instances, say *Node A* and *Node B* (being Pod or Peertube) federate with each other, in a one way federation.

### Federation

- An administrator asks for Node A to federate with Node B
- Node A reaches the [NodeInfo](https://github.com/jhass/nodeinfo/blob/main/PROTOCOL.md) endpoint (`/.well-known/nodeinfo`) on Node B and discover the root application endpoint URL.
- Node A reaches the root application endpoint (for Pod this is `/ap/`) and get the `inbox` URL.
- Node A sends a `Create` activity for a `Follow` object on the Node B root application `inbox`.
- Node B reads the Node A root application endpoint URL in the `Follow` objects, reaches this endpoint and get the Node A root application `inbox` URL.
- Node B creates a `Follower` objects and stores it locally
- Node B sends a `Accept` activity for the `Follower` object on Node A root application enpdoint.

### Video discovery

- Node A reaches the Node B root application `outbox`.
- Node B browse the pages of the `outbox` and look for announces about `Videos`
- Node B reaches the `Video` endpoints and store locally the information about the videos.

### Video creation and update sharing

- Node B publishes, edit or remove a `Video`
TBD
