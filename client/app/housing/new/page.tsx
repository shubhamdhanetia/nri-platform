import HousingForm from "../../../components/HousingForm";

export default async function NewHousingPage({ searchParams }: { searchParams: Promise<{ kind?: string }> }) {
  const { kind } = await searchParams;
  return <HousingForm initialKind={kind === "REQUEST" || kind === "TOGETHER" ? kind : "LISTING"} />;
}
