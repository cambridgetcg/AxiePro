'use client';

/**
 * React Query provider for client-side data fetching.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { config } from '@/lib/config';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: config.defaultStaleTime,
            retry: 2,
            refetchOnWindowFocus: true,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
