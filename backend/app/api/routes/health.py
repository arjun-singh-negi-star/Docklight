from botocore.exceptions import ClientError
from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthComponent, HealthResponse
from app.services.aws_clients import get_dynamodb_resource, get_s3_client
from app.services.redis_client import get_redis

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Used by Docker HEALTHCHECK and the Kubernetes liveness/readiness probes."""
    settings = get_settings()
    components = []

    try:
        get_s3_client().head_bucket(Bucket=settings.S3_BUCKET_NAME)
        components.append(HealthComponent(name="s3", healthy=True))
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            # S3 is reachable; the bucket is created lazily on the first upload.
            components.append(HealthComponent(name="s3", healthy=True, detail="bucket created on first upload"))
        else:
            components.append(HealthComponent(name="s3", healthy=False, detail=str(exc)))
    except Exception as exc:  # noqa: BLE001
        components.append(HealthComponent(name="s3", healthy=False, detail=str(exc)))

    try:
        list(get_dynamodb_resource().tables.limit(1))
        components.append(HealthComponent(name="dynamodb", healthy=True))
    except Exception as exc:  # noqa: BLE001
        components.append(HealthComponent(name="dynamodb", healthy=False, detail=str(exc)))

    try:
        get_redis().ping()
        components.append(HealthComponent(name="redis", healthy=True))
    except Exception as exc:  # noqa: BLE001
        components.append(HealthComponent(name="redis", healthy=False, detail=str(exc)))

    overall = "healthy" if all(c.healthy for c in components) else "degraded"
    return HealthResponse(status=overall, components=components)
