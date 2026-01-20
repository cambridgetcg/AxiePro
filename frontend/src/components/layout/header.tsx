"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  Menu,
  TrendingUp,
  BarChart3,
  Dna,
  Wallet,
  Home,
  Target,
  Sparkles,
  PiggyBank,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/explorer", label: "Explorer", icon: Search },
  { href: "/deals", label: "Deals", icon: Target },
  { href: "/meta", label: "Meta", icon: Sparkles, isNew: true },
  { href: "/portfolio", label: "Portfolio", icon: PiggyBank, isNew: true },
  { href: "/breeding", label: "Breeding", icon: Dna },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/logo-simple.svg"
            alt="AxiePro"
            width={36}
            height={36}
            className="rounded-lg"
          />
          <span className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            AxiePro
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              <Button variant="ghost" className="gap-2 relative">
                <item.icon className="h-4 w-4" />
                {item.label}
                {item.isNew && (
                  <Badge className="absolute -top-1 -right-1 text-[8px] px-1 py-0 h-4 bg-green-500">
                    New
                  </Badge>
                )}
              </Button>
            </Link>
          ))}
        </nav>

        {/* Right side actions */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="hidden sm:flex gap-2">
            <Wallet className="h-4 w-4" />
            Connect Wallet
          </Button>

          {/* Mobile menu */}
          <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetTrigger asChild className="md:hidden">
              <Button variant="ghost" size="icon">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[280px]">
              <div className="flex flex-col gap-4 mt-8">
                <div className="flex items-center gap-2 mb-4">
                  <Image
                    src="/logo-simple.svg"
                    alt="AxiePro"
                    width={36}
                    height={36}
                    className="rounded-lg"
                  />
                  <span className="text-xl font-bold">AxiePro</span>
                </div>
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <Button variant="ghost" className="w-full justify-start gap-2">
                      <item.icon className="h-4 w-4" />
                      {item.label}
                      {item.isNew && (
                        <Badge className="ml-auto text-[8px] px-1 py-0 h-4 bg-green-500">
                          New
                        </Badge>
                      )}
                    </Button>
                  </Link>
                ))}
                <div className="border-t pt-4 mt-4">
                  <Button variant="outline" className="w-full gap-2">
                    <Wallet className="h-4 w-4" />
                    Connect Wallet
                  </Button>
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
