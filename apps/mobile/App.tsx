import { QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "react-native";

import { queryClient } from "./src/queryClient";
import { AppShell } from "./src/screens/AppShell";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar barStyle="dark-content" />
      <AppShell />
    </QueryClientProvider>
  );
}
