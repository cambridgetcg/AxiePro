'use client';

import { useFloorPrices, useSnipes } from '@/hooks';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { PriceDisplay } from '@/components/valuation/price-display';
import { DealIndicator } from '@/components/valuation/deal-indicator';
import {
  TrendingUp,
  BarChart3,
  Target,
  Zap,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { AXIE_CLASSES } from '@/types/valuation';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function MarketPage() {
  const { data: floorData, isLoading: floorsLoading, refetch: refetchFloors } = useFloorPrices();
  const { data: snipesData, isLoading: snipesLoading, refetch: refetchSnipes } = useSnipes(5);

  const handleRefresh = () => {
    refetchFloors();
    refetchSnipes();
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Market Overview</h1>
            <p className="text-muted-foreground">
              Real-time market data and floor prices
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={floorsLoading || snipesLoading}
          >
            <RefreshCw
              className={cn(
                'h-4 w-4 mr-1',
                (floorsLoading || snipesLoading) && 'animate-spin'
              )}
            />
            Refresh
          </Button>
        </div>

        {/* Floor Prices by Class */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Floor Prices by Class
            </CardTitle>
            <CardDescription>
              Lowest listed price for each Axie class
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-4">
              {floorsLoading ? (
                AXIE_CLASSES.map((cls) => (
                  <div key={cls} className="text-center">
                    <Skeleton className="h-4 w-16 mx-auto mb-2" />
                    <Skeleton className="h-6 w-20 mx-auto" />
                  </div>
                ))
              ) : floorData?.data ? (
                AXIE_CLASSES.map((cls) => {
                  const price = floorData.data[cls];
                  return (
                    <div key={cls} className="text-center p-2 rounded-lg bg-muted/50">
                      <p className="text-xs text-muted-foreground capitalize mb-1">
                        {cls}
                      </p>
                      <PriceDisplay
                        ethValue={price ?? null}
                        size="sm"
                        className="justify-center"
                      />
                    </div>
                  );
                })
              ) : (
                <p className="col-span-full text-center text-muted-foreground">
                  Unable to load floor prices
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Latest Snipes */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-orange-500" />
                  Latest Snipe Opportunities
                </CardTitle>
                <CardDescription>
                  Best deals detected in real-time
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/deals" className="gap-1">
                  <Target className="h-4 w-4" />
                  View All
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {snipesLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
                  >
                    <div className="flex items-center gap-3">
                      <Skeleton className="h-4 w-20" />
                      <Skeleton className="h-4 w-12" />
                    </div>
                    <Skeleton className="h-6 w-16" />
                  </div>
                ))}
              </div>
            ) : snipesData?.data && snipesData.data.length > 0 ? (
              <div className="space-y-3">
                {snipesData.data.map((deal) => (
                  <div
                    key={deal.axie_id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted/70 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div>
                        <p className="font-medium">Axie #{deal.axie_id}</p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {deal.class}
                        </p>
                      </div>
                      <PriceDisplay ethValue={deal.listing_price_eth} size="sm" />
                    </div>
                    <div className="flex items-center gap-2">
                      <DealIndicator
                        discountPercent={deal.discount_percent}
                        isDeal={deal.deal_type === 'deal'}
                        isSnipe={deal.deal_type === 'snipe'}
                        size="sm"
                      />
                      <Button variant="ghost" size="sm" asChild>
                        <a
                          href={deal.marketplace_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-4">
                No snipe opportunities currently available
              </p>
            )}
          </CardContent>
        </Card>

        {/* Coming Soon Section */}
        <Card className="border-dashed">
          <CardHeader className="text-center py-12">
            <Badge variant="secondary" className="w-fit mx-auto mb-4">
              Coming Soon
            </Badge>
            <CardTitle className="text-xl">Advanced Analytics</CardTitle>
            <CardDescription className="max-w-md mx-auto">
              Price charts, sales history, volume trends, and whale tracking
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              {['Price Charts', 'Sales History', 'Volume Trends', 'Whale Tracker'].map(
                (feature) => (
                  <div key={feature} className="p-4 rounded-lg bg-muted/50">
                    <p className="text-sm font-medium">{feature}</p>
                  </div>
                )
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
