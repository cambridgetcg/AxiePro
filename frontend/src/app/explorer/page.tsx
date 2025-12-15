import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Filter, Grid, List } from "lucide-react";

export default function ExplorerPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Axie Explorer</h1>
            <p className="text-muted-foreground">
              Browse and filter Axies with advanced search
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative flex-1 md:w-80">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search by ID or name..." className="pl-10" />
            </div>
            <Button variant="outline" size="icon">
              <Filter className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon">
              <Grid className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon">
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Coming Soon Card */}
        <Card className="border-dashed">
          <CardHeader className="text-center py-16">
            <Badge variant="secondary" className="w-fit mx-auto mb-4">
              Coming Soon
            </Badge>
            <CardTitle className="text-2xl">Explorer Feature in Development</CardTitle>
            <CardDescription className="max-w-md mx-auto">
              The full Axie Explorer with advanced filtering, gene display, and real-time
              marketplace data is being built. Check back soon!
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-16">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              {["Class Filter", "Purity Filter", "Part Search", "Price Range"].map((feature) => (
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
