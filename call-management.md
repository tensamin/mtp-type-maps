# Call management protocol 1.0

`type-maps.yaml` selects application protocol version `1.0`, the only Tensamin
application dictionary. Tensamin is still in development. Call-management types
extend this dictionary without changing existing IDs or MTP's binary frame layout.

## Allocations

| Communication type | Wire ID |
| --- | --- |
| CallCommand | 226 |
| CallCommandResult | 227 |
| CallSnapshotGet | 228 |
| CallSnapshot | 229 |
| CallStateChanged | 230 |
| CallJoinAuthorize | 231 |
| CallJoinGrant | 232 |
| CallKeyEnvelopeStage | 233 |
| CallKeyEnvelopeGet | 234 |
| CallKeyEnvelopeRevoke | 235 |
| CallKeyEnvelopeActivate | 236 |
| CallKeyEpochChanged | 237 |

`DataType::CallPayload` has wire ID `256`. Communication and data IDs are
separate `u16` namespaces. IDs below 32 belong to MTP's reserved manifest.
These allocations follow `RelayReceiptPage = 225` and
`ReceiptAcceptedAt = 255`; existing gaps remain untouched.

Rust generates `CommunicationType::CallCommand`, and the other names above,
with exactly the spelling in the table. `DataType::CallPayload` is likewise a
generated enum variant. Never cast enum discriminants to obtain wire IDs.
Resolve them through the negotiated `TypeMap`.

## Dictionary selection

Native registry builds generate `TypeMap::v1_0()` and
`TypeMap::latest()`. Both select `1.0`. Without `registry`, generation uses
only the selected `protocol_version`.

All existing entries, the call operations, and `CallPayload` belong to `1.0`.
Resolve IDs through `comm_id_enum`, `data_id_enum`, or `try_to_id` before
sending. Replies must retain the request's negotiated map.

Legacy operations such as `CallInvite`, `CallToken`, `CallReserve`, `CallActivate`,
`CallEnvelopeStore`, and `CallEnvelopeGet` keep their existing allocations.
Legacy and epoch-specific envelopes are distinct protocols. A failed epoch
lookup must not return a legacy envelope instead.

Every repository's `1.0` dictionary contains the same entries and IDs,
including receipt-page fields and the call allocations above.

## Payload encoding

Each new operation carries its operation-specific, typed JSON object as UTF-8
bytes in an MTP container under `CallPayload`. Use `DataValue::Bytes`, not
`DataValue::Str`, a raw top-level JSON string, or the generic `Json` field.
This does not allocate a separate MTP field for every JSON member.

The typed models in Tau's `src/calls` define command, snapshot, event, and grant
serialization. Commands use the versioned `CallWireCommand` wrapper:

```json
{
  "version": 1,
  "request": {
    "call": {
      "owner_authority": "omikron-key:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "id": "f81b1a37-e26b-42c1-a48d-b5679b179ac4"
    },
    "operation_id": "ea7934b4-a4ae-46c7-a71c-4865cc9b969c",
    "expected_revision": 12,
    "command": { "action": "leave" }
  }
}
```

The JSON schema version `1` is separate from the MTP dictionary version `1.0`.
Commands reject unknown and duplicate fields, unsupported versions, malformed
UUIDs, and invalid typed values. The command codec bounds JSON to 16 KiB and
moderation reasons to 1024 UTF-8 bytes. The operation ID is the durable retry
identity; the outer MTP request ID only correlates a transport reply.

`CallSnapshotGet` and authenticated `CallJoinAuthorize` take
`{"version":1,"call":{...}}`. Their replies use `CallSnapshot` and `CallJoinGrant`.
`CallCommand` replies use `CallCommandResult`. Omikron wraps successful replies
as `{"version":1,"result":...}` and domain failures as
`{"version":1,"error":...}`. Requests require an outer MTP correlation ID.
`CallStateChanged` carries the typed, recipient-scoped `CallEvent` directly.
Consumers detect revision gaps and fetch a fresh requester-scoped snapshot.
The dictionary also reserves `CallKeyEpochChanged` for epoch notifications;
an allocation alone does not assert that a host emits it.

Call identities include both owner authority and UUID. Principals include both
account authority and user ID. The authenticated host session determines the
actor. A JSON actor, target ID, transport sender ID, or receiver ID does not
grant authority to perform a command.

Epoch envelope operations also use JSON bytes in `CallPayload`. Their
host-to-Iota schemas, limits, state transitions, retry behavior, and authenticated
ownership checks are specified in
[`iota/call-key-envelopes.md`](../iota/call-key-envelopes.md). Stage stores opaque
ciphertext; activation makes a staged delivery record available. It does not
prove that a client installed a key or rekeyed its media. JSON schemas on the
client-to-Omikron and Omikron-to-Iota routes differ and must not be interchanged.

## Local generation and validation

The sibling checkout layout used here is `mtp-type-maps`, `tau`, `omikron`,
`iota`, `omega`, and `client` under the same parent directory. Run from that directory:

```sh
nix shell nixpkgs#python3 -c python3 mtp-type-maps/sync-call-maps.py --check
```

Without `--check`, the script synchronizes the single `1.0` dictionary across
repositories, preserving existing allocations. It rejects duplicate IDs, reserved
IDs, and conflicting names or IDs across the mirrors. It only accepts
the flat numeric YAML schema used here. Review all map diffs after generation.

For Rust validation, run the following from `omikron`. This devshell uses the
modified canonical dictionary instead of the flake's deployed remote pin:

```sh
maps=$(realpath ../mtp-type-maps)
nix develop --override-input type-maps "path:$maps" --no-write-lock-file \
  --command env MTP_TYPE_MAPS="$maps/type-maps.yaml" \
  cargo check --locked --manifest-path ../tau/Cargo.toml

nix develop --override-input type-maps "path:$maps" --no-write-lock-file \
  --command env MTP_TYPE_MAPS="$maps/type-maps.yaml" cargo check --locked
```

Use the same `--override-input type-maps` and explicit `MTP_TYPE_MAPS` when
validating Iota or Omega in their own devshells. An ambient devshell variable
pointing into `/nix/store` may still refer to the older deployed map. Setting the
absolute canonical YAML path explicitly also lets Cargo track subsequent edits.

For the Omikron Nix package with local Omikron and type-map changes, run:

```sh
bash omikron/build-local.sh --no-link -L
```

The helper captures the local Omikron and type-map sources, including untracked
implementation files. It excludes runtime data and build output such as `.git`,
`target`, `.direnv`, and `result`. It overrides the type-map flake input with an
immutable snapshot and does not rewrite the lock file. Tau resolves through the
exact Git revision in Omikron's Cargo manifest and lock file.
`MTP_TYPE_MAPS` points to the overridden canonical YAML in the Nix store.

The Tau Cargo revision, type-map flake revision, and type-map submodule revision
are deployment inputs. Publish dependency changes before updating these pins and
the vendor hash. Validate releases with a plain `nix build --no-link`; use the
helper to check local Omikron or type-map changes before publication.
