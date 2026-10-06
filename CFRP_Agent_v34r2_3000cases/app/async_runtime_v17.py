# [NEW v17] Shared offload adapter for synchronous HTTP, disk and solver work.
import asyncio

def require_result(value=None, source=None):
    if value is None:
        raise ValueError((source or 'calculation') + ': unexpected None result; calculation blocked')
    return value

async def call_sync(function=None, args=None, kwargs=None):
    if not callable(function):
        raise ValueError('A synchronous callable is required')
    result = await asyncio.to_thread(function, *(args or ()), **(kwargs or {}))
    return require_result(result, getattr(function, '__name__', 'calculation'))

async def run_ai_async(request=None, condition=None, bundle=None, limits=None, config=None,
                       transport=None, memory=None, event_sink=None, spec=None, preview_only=None):  # [NEW v34]
    from AI import run_ai
    # [NEW v34] Keep interpretation and guard off the event loop; do not load a model for preview.
    if preview_only is True:
        return await call_sync(run_ai, kwargs=dict(request=request, condition=condition, limits=limits, config=config, transport=transport, memory=memory, event_sink=event_sink, spec=spec, preview_only=True))
    # [NEW v34r1] Load 3000-case model only after the preview return.
    if bundle is None:
        from surrogate_store_v24r1 import get_trained_bundle_v24r1
        bundle = await asyncio.to_thread(get_trained_bundle_v24r1, event_sink=event_sink)
    # [NEW v24] Prefer the separately stored 700-case development model.
    if bundle is None:
        from surrogate_store_v24 import get_trained_bundle_v24
        bundle = await asyncio.to_thread(get_trained_bundle_v24, event_sink=event_sink)
    # [NEW v23] Load/cache the trained physics surrogate off the event loop.
    # None means no saved model: existing run_ai training fallback remains available.
    if bundle is None:
        from surrogate_store_v23 import get_trained_bundle_v23
        bundle = await asyncio.to_thread(get_trained_bundle_v23, event_sink=event_sink)
    return await call_sync(run_ai, kwargs=dict(request=request, condition=condition, bundle=bundle,
        limits=limits, config=config, transport=transport, memory=memory, event_sink=event_sink, spec=spec))
