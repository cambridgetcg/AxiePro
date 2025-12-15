import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dna, Heart, Calculator, Sparkles } from "lucide-react";

export default function BreedingPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Breeding Simulator</h1>
          <p className="text-muted-foreground">
            Calculate offspring probabilities and optimize your breeding strategy
          </p>
        </div>

        {/* Parent Selection Placeholder */}
        <div className="grid md:grid-cols-2 gap-6">
          <Card className="border-dashed">
            <CardHeader className="text-center">
              <div className="h-16 w-16 mx-auto rounded-full bg-pink-500/10 flex items-center justify-center mb-4">
                <Heart className="h-8 w-8 text-pink-500" />
              </div>
              <CardTitle>Select Matron</CardTitle>
              <CardDescription>Choose the female parent Axie</CardDescription>
            </CardHeader>
            <CardContent className="text-center pb-8">
              <Button variant="outline" className="gap-2">
                <Dna className="h-4 w-4" />
                Browse Axies
              </Button>
            </CardContent>
          </Card>

          <Card className="border-dashed">
            <CardHeader className="text-center">
              <div className="h-16 w-16 mx-auto rounded-full bg-blue-500/10 flex items-center justify-center mb-4">
                <Heart className="h-8 w-8 text-blue-500" />
              </div>
              <CardTitle>Select Sire</CardTitle>
              <CardDescription>Choose the male parent Axie</CardDescription>
            </CardHeader>
            <CardContent className="text-center pb-8">
              <Button variant="outline" className="gap-2">
                <Dna className="h-4 w-4" />
                Browse Axies
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Coming Soon */}
        <Card className="border-dashed">
          <CardHeader className="text-center py-12">
            <Badge variant="secondary" className="w-fit mx-auto mb-4">
              Coming Soon
            </Badge>
            <CardTitle className="text-2xl">Advanced Breeding Tools</CardTitle>
            <CardDescription className="max-w-md mx-auto">
              Full gene probability calculations, ROI analysis, and breeding pair
              recommendations coming soon.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              {[
                { name: "Gene Calculator", icon: Dna },
                { name: "ROI Analysis", icon: Calculator },
                { name: "Best Pairs", icon: Heart },
                { name: "Rare Traits", icon: Sparkles },
              ].map((feature) => (
                <div key={feature.name} className="p-4 rounded-lg bg-muted/50 flex flex-col items-center gap-2">
                  <feature.icon className="h-5 w-5 text-muted-foreground" />
                  <p className="text-sm font-medium">{feature.name}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
