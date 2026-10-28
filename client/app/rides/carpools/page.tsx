import RideLayout from "../../../components/RideLayout";
import CarpoolList from "../../../components/CarpoolList";

export default function CarpoolsPage() {
  return <RideLayout>
    <section className="page-heading"><div><p className="eyebrow">Going the same way</p><h1>Share a planned journey.</h1><p className="muted">Find a community member already making your trip. Request seats and wait for driver approval.</p></div></section>
    <p className="ride-notice">Fixed cost-sharing contributions are per passenger, per direction. Payment is arranged outside the app. Drivers and phone numbers are not verified; transport is not guaranteed.</p>
    <CarpoolList />
  </RideLayout>;
}
