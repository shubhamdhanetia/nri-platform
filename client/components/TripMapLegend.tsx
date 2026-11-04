import { Flag, MapPin, X } from "lucide-react";

export default function TripMapLegend({
  hasSelection,
  onClearSelection,
}: {
  hasSelection: boolean;
  onClearSelection: () => void;
}) {
  return (
    <div className="ride-map-key" role="group" aria-label="Map legend and selection">
      <span><MapPin size={16} className="ride-pickup-key" aria-hidden="true" />Pickup</span>
      <span><Flag size={16} className="ride-destination-key" aria-hidden="true" />Destination</span>
      <button type="button" className="community-icon-button" title="Clear selection"
        aria-label="Clear selection" disabled={!hasSelection} onClick={onClearSelection}>
        <X size={18} />
      </button>
    </div>
  );
}
