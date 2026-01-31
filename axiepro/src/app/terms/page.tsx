import { Card, CardContent } from "@/components/ui/card";

export default function TermsPage() {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <h1 className="text-4xl font-bold mb-2">Terms of Service</h1>
      <p className="text-muted-foreground mb-8">Last updated: January 31, 2026</p>

      <Card>
        <CardContent className="prose prose-invert max-w-none p-8 space-y-8">
          {/* TL;DR Section */}
          <section className="bg-blue-900/20 p-6 rounded-lg border border-blue-800/30">
            <h2 className="text-2xl font-semibold mb-4">TL;DR: The Short Version</h2>
            <ul className="list-none space-y-2 text-muted-foreground">
              <li>✅ AxiePro is in <strong>BETA</strong> — features may change, bugs exist</li>
              <li>✅ We provide analytics, <strong>NOT financial advice</strong></li>
              <li>✅ Data sourced from SkyMavis API — may have delays or errors</li>
              <li>✅ Always DYOR (Do Your Own Research) before trading</li>
              <li>❌ We&apos;re not liable for trading losses based on our data</li>
              <li>❌ No uptime guarantees — beta is free, you&apos;ve paid $0</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Acceptance of Terms & Beta Status</h2>
            <p className="text-muted-foreground leading-relaxed">
              By accessing or using AxiePro (&quot;the Service&quot;), available at axiepro.io, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use the Service.
            </p>
            <div className="mt-4 p-4 bg-yellow-900/20 border border-yellow-800/30 rounded">
              <p className="text-yellow-200 leading-relaxed">
                <strong>🚧 Beta Status:</strong> AxiePro is currently in BETA testing. This means:
              </p>
              <ul className="list-disc list-inside text-yellow-200 mt-2 space-y-1">
                <li>Features may be added, modified, or removed without notice</li>
                <li>Data accuracy is not guaranteed (we&apos;re still testing our models)</li>
                <li>Service uptime is not guaranteed (downtime may occur)</li>
                <li>We may discontinue the beta at any time</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Description of Service</h2>
            <p className="text-muted-foreground leading-relaxed">
              AxiePro provides marketplace analytics and data visualization for the Axie Infinity ecosystem, including:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Axie marketplace data and price tracking</li>
              <li>Real-time deal detection and alerts</li>
              <li>Breeding simulation and probability calculations</li>
              <li>Market depth and liquidity analysis</li>
              <li>Historical sales trend analysis</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              <strong>What we DON&apos;T do:</strong>
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>❌ Connect to your wallet (no MetaMask, no Ronin Wallet)</li>
              <li>❌ Execute transactions or trades on your behalf</li>
              <li>❌ Store your private keys or seed phrases</li>
              <li>❌ Provide personalized investment advice</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. No Financial Advice</h2>
            <div className="p-4 bg-red-900/20 border border-red-800/30 rounded mb-4">
              <p className="text-red-200 leading-relaxed">
                ⚠️ <strong>Read this carefully:</strong> AxiePro is a data analysis tool, NOT a financial advisor.
              </p>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              The information provided by AxiePro is for informational purposes only and does not constitute financial, investment, trading, or other advice. Specifically:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>We don&apos;t recommend buying or selling any specific Axie</li>
              <li>Our valuations are estimates based on historical data and may be wrong</li>
              <li>Market conditions change rapidly — past performance ≠ future results</li>
              <li>You are 100% responsible for your own trading decisions</li>
              <li>Always conduct your own research (DYOR) before making purchases</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              <strong>Translation:</strong> We&apos;re helping you analyze data. What you do with it is up to you. Don&apos;t blame us if you buy a &quot;snipe deal&quot; and it loses value.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Data Accuracy & Limitations</h2>
            <p className="text-muted-foreground leading-relaxed mb-3">
              While we strive to provide accurate data, AxiePro makes no warranties about accuracy, completeness, or reliability:
            </p>

            <h3 className="text-xl font-medium mt-4 mb-2">Data Sources</h3>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              <li><strong>SkyMavis GraphQL API:</strong> Marketplace listings, sales, Axie metadata</li>
              <li><strong>Ronin Blockchain:</strong> On-chain transaction history</li>
              <li><strong>Our Models:</strong> Hedonic valuation based on historical sales</li>
            </ul>

            <h3 className="text-xl font-medium mt-4 mb-2">Known Limitations</h3>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              <li><strong>Data delays:</strong> 5-30 minute lag from real-time marketplace</li>
              <li><strong>API dependencies:</strong> If SkyMavis API is down, our data won&apos;t update</li>
              <li><strong>Model accuracy:</strong> Valuations are estimates, not guarantees</li>
              <li><strong>Coverage gaps:</strong> Some Axies may be missing metadata during beta</li>
              <li><strong>Market volatility:</strong> Prices can change faster than our data updates</li>
            </ul>

            <p className="text-muted-foreground leading-relaxed mt-4">
              <strong>Your responsibility:</strong> Cross-check important data with the official SkyMavis marketplace before making significant purchases.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Third-Party Data Sources & Attribution</h2>
            <p className="text-muted-foreground leading-relaxed">
              AxiePro uses the SkyMavis GraphQL API to access Axie Infinity marketplace data. We comply with SkyMavis Developer Portal terms, including:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li><strong>Attribution:</strong> All Axie data is sourced from Sky Mavis</li>
              <li><strong>Rate limits:</strong> We respect SkyMavis API rate limits (20,000 requests/day)</li>
              <li><strong>Proper use:</strong> We analyze data for analytics purposes only, no resale</li>
              <li><strong>No misrepresentation:</strong> We don&apos;t claim ownership of SkyMavis&apos;s data</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              Axie Infinity, Axie, and related trademarks are property of Sky Mavis. AxiePro is an independent analytics tool and is not affiliated with or endorsed by Sky Mavis.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. User Responsibilities</h2>
            <p className="text-muted-foreground leading-relaxed">You agree to:</p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Use the Service only for lawful purposes</li>
              <li>Not attempt to scrape, download, or mass-harvest data from the Service</li>
              <li>Not use automated scripts or bots to access the Service without permission</li>
              <li>Not attempt to reverse engineer or extract source code from the Service</li>
              <li>Not interfere with or disrupt the Service or servers</li>
              <li>Not impersonate others or misrepresent your affiliation</li>
              <li>Comply with all applicable laws and regulations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Intellectual Property</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service and its original content, features, and functionality (including our valuation models, UI/UX design, and analysis algorithms) are owned by AxiePro and are protected by international copyright, trademark, and other intellectual property laws.
            </p>
            <p className="text-muted-foreground leading-relaxed mt-3">
              Axie Infinity, Axie, and related trademarks are property of Sky Mavis. Marketplace data is sourced from SkyMavis and remains their property.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Limitation of Liability</h2>
            <div className="p-4 bg-gray-800/50 border border-gray-700 rounded mb-4">
              <p className="text-gray-300 leading-relaxed">
                📋 <strong>The Legal Part</strong> (required, but we&apos;ll make it clear):
              </p>
            </div>
            <p className="text-muted-foreground leading-relaxed mb-3">
              To the maximum extent permitted by law, AxiePro shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to:
            </p>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              <li>Trading losses from using our valuations or deal alerts</li>
              <li>Missed opportunities due to data delays or inaccuracies</li>
              <li>Service downtime, bugs, or data unavailability</li>
              <li>Third-party API failures (SkyMavis, AWS, etc.)</li>
              <li>Unauthorized access to your device or browser</li>
              <li>Any indirect, consequential, or punitive damages</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              <strong>Maximum liability:</strong> $0 (beta is free, you&apos;ve paid nothing)
            </p>
            <p className="text-muted-foreground leading-relaxed mt-3">
              <strong>Why this matters:</strong> If you buy an Axie we flagged as a &quot;snipe&quot; and lose money, you can&apos;t sue us. Our data is provided &quot;as is&quot; for educational/informational purposes. This is standard for beta analytics products.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Disclaimer of Warranties</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service is provided &quot;AS IS&quot; and &quot;AS AVAILABLE&quot; without warranties of any kind, either express or implied, including but not limited to:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>No warranty of merchantability or fitness for a particular purpose</li>
              <li>No warranty of accuracy, timeliness, or completeness of data</li>
              <li>No warranty of uninterrupted or error-free service</li>
              <li>No warranty that defects will be corrected</li>
              <li>No warranty against data loss or security breaches</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Modifications to Service</h2>
            <p className="text-muted-foreground leading-relaxed">
              AxiePro reserves the right to modify, suspend, or discontinue the Service (or any part thereof) at any time without notice. During beta, this includes:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Adding, removing, or changing features</li>
              <li>Modifying our valuation models or algorithms</li>
              <li>Adjusting data refresh rates or coverage</li>
              <li>Ending the beta and launching a paid version</li>
              <li>Discontinuing the service entirely</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              We will make reasonable efforts to notify users of major changes, but we are not obligated to do so during beta.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Termination</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may terminate or suspend access to the Service immediately, without prior notice or liability, for any reason, including breach of these Terms. Upon termination, your right to use the Service will immediately cease.
            </p>
            <p className="text-muted-foreground leading-relaxed mt-3">
              When the beta phase ends, we may transition to a paid service. Beta users will be notified before any charges are applied.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. Changes to These Terms</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may update these Terms of Service from time to time. We will notify you of any changes by:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Posting the new Terms on this page</li>
              <li>Updating the &quot;Last updated&quot; date at the top</li>
              <li>Displaying a banner notification on the site (for major changes)</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              Your continued use of the Service after any changes constitutes acceptance of the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">13. Governing Law</h2>
            <p className="text-muted-foreground leading-relaxed">
              These Terms shall be governed by and construed in accordance with applicable laws, without regard to conflict of law principles. Any disputes arising from these Terms or your use of the Service shall be subject to the exclusive jurisdiction of the applicable courts.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">14. Contact</h2>
            <p className="text-muted-foreground leading-relaxed">
              If you have any questions about these Terms of Service, please contact us at:
            </p>
            <p className="text-muted-foreground mt-2">
              Email: <a href="mailto:contact@axiepro.io" className="text-primary hover:underline">contact@axiepro.io</a>
            </p>
          </section>

          {/* Beta Acknowledgment */}
          <section className="bg-blue-900/20 p-6 rounded-lg border border-blue-800/30">
            <h2 className="text-xl font-semibold mb-3">Beta User Acknowledgment</h2>
            <p className="text-muted-foreground leading-relaxed">
              By using AxiePro during the beta phase, you acknowledge that:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>You understand this is a beta product with limitations</li>
              <li>You will not rely solely on AxiePro data for trading decisions</li>
              <li>You accept the risks of using pre-release software</li>
              <li>You will provide feedback to help improve the service</li>
              <li>You understand features may change or be removed</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              Thank you for being an early adopter and helping us build a better analytics platform! 🙏
            </p>
          </section>
        </CardContent>
      </Card>
    </div>
  );
}
