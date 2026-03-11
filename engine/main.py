# --- L9_META ---
# l9_schema: 1
# layer: [api]
# tags: [fastapi, chassis, entrypoint]
# status: active
# --- /L9_META ---
"""l9-codegraph — chassis entrypoint. Single ingress via PacketEnvelope."""
from chassis.chassis_app import create_app
from engine.boot import CodegraphLifecycle

app = create_app(lifecycle_hook=CodegraphLifecycle())
