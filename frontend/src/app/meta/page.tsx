'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import {
  RefreshCw,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Activity,
  Filter,
  Info,
} from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { MetaSummaryCard, MetaShiftCard, MetaShiftCardSkeleton } from '@/components/meta';
import {
  useMetaSummary,
  useRisingMeta,
  useFallingMeta,
  useEmergingMeta,
  useFadingMeta,
} from '@/hooks/use-meta';
import { cn } from '@/lib/utils';
import type { ShiftType } from '@/types/meta';

type TabValue = 'all' | ShiftType;

export default function MetaPage() {
  const [activeTab, setActiveTab] = useState<TabValue>('all');
  const [minConfidence, setMinConfidence] = useState(25);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch meta data
  const { data: summaryData, isLoading: summaryLoading, refetch: refetchSummary } = useMetaSummary();
  const { data: risingData, isLoading: risingLoading, refetch: refetchRising } = useRisingMeta(50, minConfidence);
  const { data: fallingData, isLoading: fallingLoading, refetch: refetchFalling } = useFallingMeta(50, minConfidence);
  const { data: emergingData, isLoading: emergingLoading, refetch: refetchEmerging } = useEmergingMeta(50, minConfidence);
  const { data: fadingData, isLoading: fadingLoading, refetch: refetchFading } = useFadingMeta(50, minConfidence);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([
      refetchSummary(),
      refetchRising(),
      refetchFalling(),
      refetchEmerging(),
      refetchFading(),
    ]);
    setIsRefreshing(false);
  };

  // Filter shifts by confidence
  const filterByConfidence = <T extends { confidence: number }>(shifts: T[] | undefined) => {
    return shifts?.filter((s) => s.confidence >= minConfidence) || [];
  };

  const risingShifts = filterByConfidence(risingData?.shifts);
  const fallingShifts = filterByConfidence(fallingData?.shifts);
  const emergingShifts = filterByConfidence(emergingData?.shifts);
  const fadingShifts = filterByConfidence(fadingData?.shifts);

  const allShifts = [...risingShifts, ...fallingShifts, ...emergingShifts, ...fadingShifts]
    .sort((a, b) => b.confidence - a.confidence);

  const isLoading = risingLoading || fallingLoading || emergingLoading || fadingLoading;

  const getShiftsForTab = () => {
    switch (activeTab) {
      case 'rising':
        return risingShifts;
      case 'falling':
        return fallingShifts;
      case 'emerging':
        return emergingShifts;
      case 'fading':
        return fadingShifts;
      default:
        return allShifts;
    }
  };

  const currentShifts = getShiftsForTab();

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-primary" />
              Meta Shifts
            </h1>
            <p className="text-muted-foreground">
              Detect emerging trends and shifting market dynamics before they become obvious
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn('h-4 w-4 mr-1', isRefreshing && 'animate-spin')}
              />
              Refresh
            </Button>
          </div>
        </div>

        {/* Summary Overview */}
        <MetaSummaryCard summary={summaryData?.summary} isLoading={summaryLoading} />

        {/* Confidence Filter */}
        <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Minimum Confidence</span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-3 w-3 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">
                    Filter signals by confidence score. Higher confidence means more
                    aligned indicators (price, volume, trend).
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <div className="flex-1 max-w-xs">
            <Slider
              value={[minConfidence]}
              onValueChange={([value]) => setMinConfidence(value)}
              min={0}
              max={100}
              step={5}
            />
          </div>
          <Badge variant="secondary" className="min-w-[4rem] justify-center">
            {minConfidence}%
          </Badge>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabValue)}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="all" className="flex items-center gap-1">
              All
              <Badge variant="secondary" className="ml-1 text-xs">
                {allShifts.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="rising" className="flex items-center gap-1">
              <TrendingUp className="h-4 w-4 text-green-500" />
              Rising
              <Badge variant="secondary" className="ml-1 text-xs">
                {risingShifts.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="falling" className="flex items-center gap-1">
              <TrendingDown className="h-4 w-4 text-red-500" />
              Falling
              <Badge variant="secondary" className="ml-1 text-xs">
                {fallingShifts.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="emerging" className="flex items-center gap-1">
              <Sparkles className="h-4 w-4 text-blue-500" />
              Emerging
              <Badge variant="secondary" className="ml-1 text-xs">
                {emergingShifts.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="fading" className="flex items-center gap-1">
              <Activity className="h-4 w-4 text-orange-500" />
              Fading
              <Badge variant="secondary" className="ml-1 text-xs">
                {fadingShifts.length}
              </Badge>
            </TabsTrigger>
          </TabsList>

          <TabsContent value={activeTab} className="mt-6">
            {isLoading ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <MetaShiftCardSkeleton key={i} />
                ))}
              </div>
            ) : currentShifts.length === 0 ? (
              <div className="text-center py-12 bg-muted/30 rounded-lg">
                <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No Shifts Detected</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  No meta shifts match your current filter criteria.
                  Try lowering the minimum confidence threshold.
                </p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {currentShifts.map((shift, index) => (
                  <MetaShiftCard key={`${shift.trait_key}-${index}`} shift={shift} />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Methodology Info */}
        <section className="text-center py-4 border-t">
          <p className="text-xs text-muted-foreground">
            Meta shifts are detected by analyzing price velocity, volume changes, and market trends.
            <br />
            Confidence scores reflect alignment between multiple signals. Higher confidence = stronger signal.
          </p>
        </section>
      </div>
    </div>
  );
}
