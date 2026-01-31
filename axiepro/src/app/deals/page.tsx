'use client';
// Deal Discovery page - find undervalued Axies

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
import { DealDetailCard, DealDetailCardSkeleton } from '@/components/deals';
import {
  Target,
  Zap,
  RefreshCw,
  Filter,
  LayoutGrid,
  LayoutList,
} from 'lucide-react';
import { AXIE_CLASSES, type AxieClass } from '@/types/valuation';
import { cn } from '@/lib/utils';

type ViewMode = 'grid' | 'list';

type TabType = 'deals' | 'snipes';

export default function DealsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('deals');
  const [selectedClass, setSelectedClass] = useState<AxieClass | undefined>();
  const [minScore, setMinScore] = useState(50);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

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
            {/* View Mode Toggle */}
            <div className="flex items-center border rounded-lg">
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className="rounded-r-none"
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                className="rounded-l-none"
              >
                <LayoutList className="h-4 w-4" />
              </Button>
            </div>
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
        <div
          className={cn(
            'gap-4',
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3'
              : 'flex flex-col'
          )}
        >
          {isLoading ? (
            // Loading skeletons
            Array.from({ length: 6 }).map((_, i) => (
              <DealDetailCardSkeleton key={i} />
            ))
          ) : data?.data && data.data.length > 0 ? (
            data.data.map((deal) => (
              <DealDetailCard
                key={deal.axie_id}
                deal={deal}
                className={viewMode === 'list' ? 'max-w-3xl' : undefined}
              />
            ))
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
