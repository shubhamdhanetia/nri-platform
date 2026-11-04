import type { PostType } from "../lib/api";

export default function ParkingNotice({ postType, compact = false }: {
  postType: PostType | "";
  compact?: boolean;
}) {
  if (postType !== "OFFER" && postType !== "REQUEST") return null;

  if (compact) return <aside className="parking-notice" aria-label="Parking guidance">
    Confirm availability and arrangements directly; a post is not a reservation.
  </aside>;

  return <aside className="parking-notice" aria-label="Parking guidance">
    <strong>{postType === "OFFER" ? "Parking available" : "Parking wanted"}</strong>
    {postType === "OFFER"
      ? <p>Include availability, price and pricing period, vehicle restrictions, and how interested members can contact you. Check that you have permission to rent out the space.</p>
      : <p>Include your preferred area, dates or duration, budget and pricing period, vehicle size, and how members can contact you.</p>}
    <p>Your selected location and any contact details follow your post&apos;s visibility setting. Use a nearby landmark if you prefer not to display the exact address. Share gate codes and access credentials privately, never in the post.</p>
  </aside>;
}
