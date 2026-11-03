import { Suspense } from "react";

import { Loading, Screen } from "@/components/ui";

import { VerifyToken } from "./verify-token";

// useSearchParams kullanan bileşen Suspense içinde olmalı (Next.js 16).
export default function VerifyPage() {
  return (
    <Screen title="Giriş yapılıyor">
      <Suspense fallback={<Loading />}>
        <VerifyToken />
      </Suspense>
    </Screen>
  );
}
