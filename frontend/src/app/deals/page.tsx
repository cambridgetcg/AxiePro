'use client';

import { useState } from 'react';
import { useDeals, useSnipes } from '@/hooks';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PriceDisplay } from '@/components/valuation/price-display';
import { DealIndicator } from '@/components/valuation/deal-indicator';
import {
  Target,
  Zap,
  RefreshCw,
  ExternalLink,
  Filter,
} from 'lucide-react';
import { AXIE_CLASSES, type AxieClass, type Deal } from '@/types/valuation';
import { cn } from '@/lib/utils';

type TabType = 'deals' | 'snipes';

export default function DealsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('deals');
  const [selectedClass, setSelectedClass] = useState<AxieClass | undefined>();
  const [minScore, setMinScore] = useState(50);

  // Fetch data based on active tab
  const dealsQuery = useDeals(
    activeTab === 'deals' ? { class: selectedClass, minScore } : undefined
  );
  const snipesQuery = useSnipes(20);

  const isLoading =
    activeTab === 'deals' ? dealsQuery.isLoading : snipesQuery.isLoading;
  const data = activeTab === 'deals' ? dealsQuery.data : snipesQuery.data;
  const refetch = activeTab === 'deals' ? dealsQuery.refetch : snipesQuery.refetch;
  const dataUpdatedAt =
    activeTab === 'deals' ? dealsQuery.dataUpdatedAt : snipesQuery.dataUpdatedAt;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Deal Discovery</h1>
            <p className="text-muted-foreground">
              Find undervalued Axies in real-time
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              <RefreshCw
                className={cn('h-4 w-4 mr-1', isLoading && 'animate-spin')}
              />
              Refresh
            </Button>
            {dataUpdatedAt && (
              <span className="text-xs text-muted-foreground">
                Updated: {new Date(dataUpdatedAt).toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 border-b pb-2">
          <Button
            variant={activeTab === 'deals' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('deals')}
            className="gap-1"
          >
            <Target className="h-4 w-4" />
            Deals
          </Button>
          <Button
            variant={activeTab === 'snipes' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('snipes')}
            className="gap-1"
          >
            <Zap className="h-4 w-4" />
            Snipes
          </Button>
        </div>

        {/* Filters (only for deals tab) */}
        {activeTab === 'deals' && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1">
                <Filter className="h-4 w-4" />
                Filters
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                {/* Class Filter */}
                <div>
                  <p className="text-xs text-muted-foreground mb-2">Class</p>
                  <div className="flex flex-wrap gap-1">
                    <Button
                      variant={selectedClass === undefined ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setSelectedClass(undefined)}
                    >
                      All
                    </Button>
                    {AXIE_CLASSES.map((cls) => (
                      <Button
                        key={cls}
                        variant={selectedClass === cls ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setSelectedClass(cls)}
                        className="capitalize"
                      >
                        {cls}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Min Score Filter */}
                <div>
                  <p className="text-xs text-muted-foreground mb-2">
                    Min Score: {minScore}
                  </p>
                  <input
                    type="range"
                    min="50"
                    max="100"
                    value={minScore}
                    onChange={(e) => setMinScore(Number(e.target.value))}
                    className="w-32"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {isLoading ? (
            // Loading skeletons
            Array.from({ length: 6 }).map((_, i) => (
              <DealCardSkeleton key={i} />
            ))
          ) : data?.data && data.data.length > 0 ? (
            data.data.map((deal) => <DealCard key={deal.axie_id} deal={deal} />)
          ) : (
            <Card className="col-span-full">
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">
                  No {activeTab === 'deals' ? 'deals' : 'snipes'} found.
                  {activeTab === 'deals' && ' Try adjusting your filters.'}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Result count */}
        {data?.meta && (
          <p className="text-sm text-muted-foreground text-center">
            Showing {data.data.length} {activeTab}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Individual deal card component.
 */
function DealCard({ deal }: { deal: Deal }) {
  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">Axie #{deal.axie_id}</CardTitle>
            <CardDescription className="capitalize">
              {deal.class}
            </CardDescription>
          </div>
          <DealIndicator
            discountPercent={deal.discount_percent}
            isDeal={deal.deal_type === 'deal'}
            isSnipe={deal.deal_type === 'snipe'}
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <p className="text-xs text-muted-foreground">Listing</p>
            <PriceDisplay ethValue={deal.listing_price_eth} size="md" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Fair Value</p>
            <PriceDisplay ethValue={deal.fair_value_eth} size="md" />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t">
          <Badge variant="secondary">Score: {deal.deal_score}</Badge>
          <Button variant="outline" size="sm" asChild>
            <a
              href={deal.marketplace_url}
              target="_blank"
              rel="noopener noreferrer"
              className="gap-1"
            >
              <ExternalLink className="h-3 w-3" />
              View
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Loading skeleton for deal card.
 */
function DealCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-4 w-16" />
          </div>
          <Skeleton className="h-6 w-16" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-5 w-20" />
          </div>
          <div className="space-y-1">
            <Skeleton className="h-3 w-14" />
            <Skeleton className="h-5 w-20" />
          </div>
        </div>
        <div className="flex items-center justify-between pt-2 border-t">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-8 w-16" />
        </div>
      </CardContent>
    </Card>
  );
}
