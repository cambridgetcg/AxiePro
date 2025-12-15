import { Card, CardContent } from "@/components/ui/card";

export default function TermsPage() {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <h1 className="text-4xl font-bold mb-2">Terms of Service</h1>
      <p className="text-muted-foreground mb-8">Last updated: December 15, 2025</p>

      <Card>
        <CardContent className="prose prose-invert max-w-none p-8 space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Acceptance of Terms</h2>
            <p className="text-muted-foreground leading-relaxed">
              By accessing or using AxiePro (&quot;the Service&quot;), available at axiepro.io, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Description of Service</h2>
            <p className="text-muted-foreground leading-relaxed">
              AxiePro provides market analytics, data visualization, and tools for the Axie Infinity ecosystem, including but not limited to:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Axie marketplace data and price tracking</li>
              <li>Breeding simulation and probability calculations</li>
              <li>Market trend analysis and alerts</li>
              <li>Portfolio tracking tools</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. No Financial Advice</h2>
            <p className="text-muted-foreground leading-relaxed">
              The information provided by AxiePro is for informational purposes only and does not constitute financial, investment, trading, or other advice. You should not treat any of the Service&apos;s content as such. AxiePro does not recommend that any cryptocurrency or NFT should be bought, sold, or held by you. You are solely responsible for your own investment decisions.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Data Accuracy</h2>
            <p className="text-muted-foreground leading-relaxed">
              While we strive to provide accurate and up-to-date information, AxiePro makes no warranties or representations regarding the accuracy, completeness, or reliability of any data displayed on the Service. Market data is sourced from third-party APIs and blockchain data, which may contain errors or delays.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. User Responsibilities</h2>
            <p className="text-muted-foreground leading-relaxed">You agree to:</p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Use the Service only for lawful purposes</li>
              <li>Not attempt to interfere with or disrupt the Service</li>
              <li>Not use automated scripts or bots to access the Service without permission</li>
              <li>Not attempt to reverse engineer or extract source code from the Service</li>
              <li>Comply with all applicable laws and regulations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Intellectual Property</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service and its original content, features, and functionality are owned by AxiePro and are protected by international copyright, trademark, and other intellectual property laws. Axie Infinity, Axie, and related trademarks are property of Sky Mavis.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Third-Party Links and Services</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service may contain links to third-party websites or services, including the Axie Infinity marketplace. AxiePro is not responsible for the content, privacy policies, or practices of any third-party sites or services.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Limitation of Liability</h2>
            <p className="text-muted-foreground leading-relaxed">
              To the maximum extent permitted by law, AxiePro shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to loss of profits, data, or other intangible losses, resulting from:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Your use or inability to use the Service</li>
              <li>Any trading or investment decisions made based on information from the Service</li>
              <li>Unauthorized access to your data</li>
              <li>Errors or inaccuracies in the data provided</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Disclaimer of Warranties</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service is provided &quot;as is&quot; and &quot;as available&quot; without warranties of any kind, either express or implied, including but not limited to implied warranties of merchantability, fitness for a particular purpose, and non-infringement.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Modifications to Service</h2>
            <p className="text-muted-foreground leading-relaxed">
              AxiePro reserves the right to modify, suspend, or discontinue the Service at any time without notice. We may also update these Terms of Service from time to time. Continued use of the Service after any changes constitutes acceptance of the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Governing Law</h2>
            <p className="text-muted-foreground leading-relaxed">
              These Terms shall be governed by and construed in accordance with applicable laws, without regard to conflict of law principles.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. Contact</h2>
            <p className="text-muted-foreground leading-relaxed">
              If you have any questions about these Terms of Service, please contact us at contact@axiepro.io.
            </p>
          </section>
        </CardContent>
      </Card>
    </div>
  );
}
