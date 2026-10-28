from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer


class UTCResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("pickup_start", "pickup_end", "pickup_time", "created_at", check_fields=False)
    def serialize_datetime(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat()
