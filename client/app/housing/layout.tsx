import type { ReactNode } from "react";
import HousingLayout from "../../components/HousingLayout";
import "./housing.css";

export default function Layout({ children }: { children: ReactNode }) {
  return <HousingLayout>{children}</HousingLayout>;
}
