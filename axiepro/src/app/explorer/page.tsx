'use client';

import { useState } from 'react';
import { useValuation } from '@/hooks';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  ValuationCard,
  ValuationCardSkeleton,
} from '@/components/valuation';
import { Search, Loader2 } from 'lucide-react';

export default function ExplorerPage() {
  const [searchInput, setSearchInput] = useState('');
  const [searchedId, setSearchedId] = useState<number | null>(null);

  const {
    data: valuation,
    isLoading,
    isError,
    error,
  } = useValuation(searchedId);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(searchInput.trim(), 10);
    if (!isNaN(id) && id > 0) {
      setSearchedId(id);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Axie Explorer</h1>
          <p className="text-muted-foreground">
            Look up any Axie by ID to get its fair market valuation
          </p>
        </div>

        {/* Search */}
        <Card>
          <CardHeader>
            <CardTitle>Axie Valuation Lookup</CardTitle>
            <CardDescription>
              Enter an Axie ID to get its estimated fair market value
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  placeholder="Enter Axie ID (e.g., 12345)"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Button type="submit" disabled={!searchInput.trim() || isLoading}>
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Get Valuation'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Results */}
        {searchedId !== null && (
          <div className="max-w-xl">
            {isLoading ? (
              <ValuationCardSkeleton />
            ) : isError ? (
              <Card>
                <CardContent className="py-8 text-center">
                  <p className="text-destructive mb-2">Failed to load valuation</p>
                  <p className="text-sm text-muted-foreground mb-4">
                    {error instanceof Error
                      ? error.message.includes('404')
                        ? `Axie #${searchedId} not found or has insufficient data`
                        : error.message
                      : 'Unknown error occurred'}
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => setSearchedId(null)}
                  >
                    Try Another
                  </Button>
                </CardContent>
              </Card>
            ) : valuation ? (
              <ValuationCard valuation={valuation} showFeatureBreakdown />
            ) : null}
          </div>
        )}

        {/* Coming Soon Features */}
        <Card className="border-dashed">
          <CardHeader className="text-center py-12">
            <Badge variant="secondary" className="w-fit mx-auto mb-4">
              Coming Soon
            </Badge>
            <CardTitle className="text-xl">Advanced Explorer Features</CardTitle>
            <CardDescription className="max-w-md mx-auto">
              Browse, filter, and compare Axies with advanced search
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              {[
                'Class Filter',
                'Part Search',
                'Price Range',
                'Gene Display',
              ].map((feature) => (
                <div key={feature} className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm font-medium">{feature}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
