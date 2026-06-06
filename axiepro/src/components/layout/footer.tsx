import Link from "next/link";
import Image from "next/image";
import { Separator } from "@/components/ui/separator";

export function Footer() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
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
            <p className="text-sm text-muted-foreground">
              Advanced market analytics and tools for Axie Infinity traders and breeders.
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="font-semibold mb-3">Product</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link href="/explorer" className="hover:text-foreground transition-colors">
                  Explorer
                </Link>
              </li>
              <li>
                <Link href="/deals" className="hover:text-foreground transition-colors">
                  Deals
                </Link>
              </li>
              <li>
                <Link href="/analytics" className="hover:text-foreground transition-colors">
                  Analytics
                </Link>
              </li>
              <li>
                <Link href="/portfolio" className="hover:text-foreground transition-colors">
                  Portfolio
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h3 className="font-semibold mb-3">Resources</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <a
                  href="https://api.axiepro.io/api/v1/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  API Documentation
                </a>
              </li>
              <li>
                <a
                  href="https://docs.axieinfinity.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  Axie Wiki
                </a>
              </li>
              <li>
                <a
                  href="https://axieinfinity.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  Axie Infinity
                </a>
              </li>
            </ul>
          </div>
        </div>

        <Separator className="my-8" />

        <p className="text-xs text-muted-foreground mb-4 text-center md:text-left">
          AxiePro is read-only and non-custodial — it never touches your funds. Information is
          provided for research only and is{" "}
          <span className="font-medium text-foreground">not financial advice</span>. Do your own research.
        </p>

        <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} AxiePro. All rights reserved.</p>
          <div className="flex gap-4">
            <Link href="/privacy" className="hover:text-foreground transition-colors">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-foreground transition-colors">
              Terms
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
