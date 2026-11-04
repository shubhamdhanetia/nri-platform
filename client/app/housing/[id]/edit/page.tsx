"use client";

import { useParams } from "next/navigation";
import HousingForm from "../../../../components/HousingForm";
import { HousingLoadState } from "../../../../components/HousingControls";
import { useHousingResource, type HousingItem } from "../../../../lib/housing";
import type { User } from "../../../../lib/api";

export default function EditHousingPage() {
  const { id } = useParams<{ id: string }>();
  const item = useHousingResource<HousingItem>(`/housing/${id}`);
  const user = useHousingResource<User>("/users/me");
  if (item.loading || item.error) return <HousingLoadState loading={item.loading} error={item.error} retry={item.reload} />;
  if (user.loading || user.error) return <HousingLoadState loading={user.loading} error={user.error} retry={user.reload} />;
  if (!item.data || !user.data) return null;
  if (item.data.owner_id !== user.data.id) return <div className="state-card" role="alert">Only the owner can edit this housing post.</div>;
  return <HousingForm key={item.data.id} item={item.data} />;
}
