import HousingDetail from "../../../components/HousingDetail";

export default async function HousingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <HousingDetail key={id} id={id} />;
}
