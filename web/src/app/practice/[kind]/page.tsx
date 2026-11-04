import { Suspense } from "react";

import { Loading, Screen } from "@/components/ui";

import { ExtraPractice } from "./extra-practice";

// useParams kullanan bileşen Suspense içinde olmalı (Next.js 16).
export default function ExtraPracticePage() {
  return (
    <Suspense
      fallback={
        <Screen>
          <Loading />
        </Screen>
      }
    >
      <ExtraPractice />
    </Suspense>
  );
}
