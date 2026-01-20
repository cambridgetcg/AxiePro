'use client';

/**
 * Holdings Table - Shows individual Axie holdings with P&L.
 */
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Edit2,
  ExternalLink,
  AlertCircle,
  ArrowUpDown,
} from 'lucide-react';
import type { HoldingWithPnL, AcquisitionType } from '@/types/portfolio';

interface HoldingsTableProps {
  holdings: HoldingWithPnL[] | undefined;
  isLoading?: boolean;
  onUpdateCostBasis?: (
    axieId: number,
    costBasisEth: number,
    acquisitionType?: AcquisitionType,
    acquiredAt?: string
  ) => void;
  className?: string;
}

type SortField = 'axie_id' | 'unrealized_pnl' | 'cost_basis' | 'current_value';
type SortOrder = 'asc' | 'desc';

export function HoldingsTable({
  holdings,
  isLoading,
  onUpdateCostBasis,
  className,
}: HoldingsTableProps) {
  const [sortField, setSortField] = useState<SortField>('unrealized_pnl');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  if (isLoading) {
    return <HoldingsTableSkeleton className={className} />;
  }

  if (!holdings || holdings.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Holdings Found</h3>
            <p className="text-sm text-muted-foreground">
              This wallet doesn&apos;t have any Axie holdings to display.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const sortedHoldings = [...holdings].sort((a, b) => {
    const getValue = (h: HoldingWithPnL, field: SortField): number => {
      switch (field) {
        case 'axie_id':
          return h.axie_id;
        case 'unrealized_pnl':
          return h.unrealized_pnl_eth ?? -Infinity;
        case 'cost_basis':
          return h.cost_basis_eth ?? -Infinity;
        case 'current_value':
          return h.current_value_eth ?? -Infinity;
        default:
          return 0;
      }
    };
    const aVal = getValue(a, sortField);
    const bVal = getValue(b, sortField);
    return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const SortableHeader = ({
    field,
    children,
  }: {
    field: SortField;
    children: React.ReactNode;
  }) => (
    <TableHead
      className="cursor-pointer hover:bg-muted/50"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        <ArrowUpDown className="h-3 w-3" />
      </div>
    </TableHead>
  );

  const missingCostBasisCount = holdings.filter((h) => !h.has_cost_basis).length;

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Holdings</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{holdings.length} Axies</Badge>
            {missingCostBasisCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {missingCostBasisCount} missing cost basis
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHeader field="axie_id">Axie ID</SortableHeader>
                <TableHead>Class</TableHead>
                <SortableHeader field="cost_basis">Cost Basis</SortableHeader>
                <SortableHeader field="current_value">Current Value</SortableHeader>
                <SortableHeader field="unrealized_pnl">P&L</SortableHeader>
                <TableHead>ROI</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedHoldings.map((holding) => (
                <HoldingRow
                  key={holding.axie_id}
                  holding={holding}
                  onUpdateCostBasis={onUpdateCostBasis}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

interface HoldingRowProps {
  holding: HoldingWithPnL;
  onUpdateCostBasis?: (
    axieId: number,
    costBasisEth: number,
    acquisitionType?: AcquisitionType,
    acquiredAt?: string
  ) => void;
}

function HoldingRow({ holding, onUpdateCostBasis }: HoldingRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [costBasis, setCostBasis] = useState(
    holding.cost_basis_eth?.toString() || ''
  );
  const [acquisitionType, setAcquisitionType] = useState<AcquisitionType>(
    holding.acquisition_type || 'purchase'
  );

  const isProfitable = (holding.unrealized_pnl_eth ?? 0) >= 0;
  const hasCostBasis = holding.has_cost_basis;

  const handleSave = () => {
    const value = parseFloat(costBasis);
    if (!isNaN(value) && value >= 0 && onUpdateCostBasis) {
      onUpdateCostBasis(holding.axie_id, value, acquisitionType);
      setIsEditing(false);
    }
  };

  const PnLIcon = isProfitable ? TrendingUp : hasCostBasis ? TrendingDown : Minus;
  const pnlColor = !hasCostBasis
    ? 'text-muted-foreground'
    : isProfitable
    ? 'text-green-500'
    : 'text-red-500';

  return (
    <TableRow>
      <TableCell>
        <a
          href={`https://app.axieinfinity.com/marketplace/axies/${holding.axie_id}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 hover:underline text-primary"
        >
          #{holding.axie_id}
          <ExternalLink className="h-3 w-3" />
        </a>
      </TableCell>
      <TableCell>
        {holding.class ? (
          <Badge variant="outline" className="capitalize">
            {holding.class}
          </Badge>
        ) : (
          <span className="text-muted-foreground">-</span>
        )}
      </TableCell>
      <TableCell>
        {hasCostBasis ? (
          <span>{holding.cost_basis_eth?.toFixed(4)} ETH</span>
        ) : (
          <span className="text-yellow-600 flex items-center gap-1">
            <AlertCircle className="h-3 w-3" />
            Not set
          </span>
        )}
      </TableCell>
      <TableCell>
        {holding.current_value_eth !== null ? (
          <span>{holding.current_value_eth.toFixed(4)} ETH</span>
        ) : (
          <span className="text-muted-foreground">-</span>
        )}
      </TableCell>
      <TableCell>
        <div className={cn('flex items-center gap-1', pnlColor)}>
          <PnLIcon className="h-4 w-4" />
          {holding.unrealized_pnl_eth !== null ? (
            <span>
              {isProfitable ? '+' : ''}
              {holding.unrealized_pnl_eth.toFixed(4)} ETH
            </span>
          ) : (
            <span className="text-muted-foreground">-</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        {holding.unrealized_pnl_percent !== null ? (
          <Badge
            variant={isProfitable ? 'default' : 'destructive'}
            className={cn(
              isProfitable ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
            )}
          >
            {isProfitable ? '+' : ''}
            {holding.unrealized_pnl_percent.toFixed(1)}%
          </Badge>
        ) : (
          <span className="text-muted-foreground">-</span>
        )}
      </TableCell>
      <TableCell className="text-right">
        <Dialog open={isEditing} onOpenChange={setIsEditing}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm">
              <Edit2 className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Cost Basis</DialogTitle>
              <DialogDescription>
                Set the acquisition cost for Axie #{holding.axie_id}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label className="text-sm font-medium">Cost Basis (ETH)</label>
                <Input
                  type="number"
                  step="0.0001"
                  min="0"
                  placeholder="0.00"
                  value={costBasis}
                  onChange={(e) => setCostBasis(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium">Acquisition Type</label>
                <Select
                  value={acquisitionType}
                  onValueChange={(v) => setAcquisitionType(v as AcquisitionType)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="purchase">Purchase</SelectItem>
                    <SelectItem value="breed">Bred</SelectItem>
                    <SelectItem value="gift">Gift / Airdrop</SelectItem>
                    <SelectItem value="unknown">Unknown</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
              <Button onClick={handleSave}>Save</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </TableCell>
    </TableRow>
  );
}

function HoldingsTableSkeleton({ className }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-5 w-20" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                {[1, 2, 3, 4, 5, 6, 7].map((i) => (
                  <TableHead key={i}>
                    <Skeleton className="h-4 w-16" />
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {[1, 2, 3, 4, 5].map((i) => (
                <TableRow key={i}>
                  {[1, 2, 3, 4, 5, 6, 7].map((j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
