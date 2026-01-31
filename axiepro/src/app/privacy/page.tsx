import { Card, CardContent } from "@/components/ui/card";

export default function PrivacyPage() {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <h1 className="text-4xl font-bold mb-2">Privacy Policy</h1>
      <p className="text-muted-foreground mb-8">Last updated: January 31, 2026</p>

      <Card>
        <CardContent className="prose prose-invert max-w-none p-8 space-y-8">
          {/* TL;DR Section */}
          <section className="bg-blue-900/20 p-6 rounded-lg border border-blue-800/30">
            <h2 className="text-2xl font-semibold mb-4">TL;DR: The Short Version</h2>

            <h3 className="text-lg font-medium mt-3 mb-2">What we collect:</h3>
            <ul className="list-none space-y-1 text-muted-foreground">
              <li>✅ Public blockchain data (anyone can see this)</li>
              <li>✅ Anonymous usage analytics (which pages you visit)</li>
            </ul>

            <h3 className="text-lg font-medium mt-4 mb-2">What we DON&apos;T collect:</h3>
            <ul className="list-none space-y-1 text-muted-foreground">
              <li>❌ Your wallet address or private keys</li>
              <li>❌ Personal information (name, email, etc.)</li>
              <li>❌ Your IP address or precise location</li>
            </ul>

            <h3 className="text-lg font-medium mt-4 mb-2">How we use it:</h3>
            <ul className="list-none space-y-1 text-muted-foreground">
              <li>• Display Axie marketplace analytics</li>
              <li>• Improve the platform based on usage patterns</li>
              <li>• Detect abuse (excessive API calls)</li>
            </ul>

            <p className="text-muted-foreground mt-4">
              <strong>Bottom line:</strong> We&apos;re a read-only analytics tool. We look at public data and show you insights. We don&apos;t touch your wallet, and we don&apos;t sell your data.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
            <p className="text-muted-foreground leading-relaxed">
              AxiePro (&quot;we&quot;, &quot;our&quot;, or &quot;us&quot;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website axiepro.io and use our services.
            </p>
            <div className="mt-4 p-4 bg-green-900/20 border border-green-800/30 rounded">
              <p className="text-green-200 leading-relaxed">
                🔒 <strong>Key Point:</strong> During beta, AxiePro operates as a <strong>read-only analytics tool</strong>. We do NOT connect to your wallet, we do NOT ask for personal information, and we do NOT store sensitive data. This policy describes what little data we do collect.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Information We Collect</h2>

            <h3 className="text-xl font-medium mt-4 mb-2">2.1 Public Blockchain Data</h3>
            <p className="text-muted-foreground leading-relaxed">
              We READ publicly available blockchain data from the Ronin network and SkyMavis GraphQL API, including:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Axie marketplace listings (prices, classes, parts)</li>
              <li>Historical sales transactions (amounts, timestamps)</li>
              <li>Axie metadata (genes, breed counts, stats)</li>
              <li>NFT ownership records (publicly visible wallet addresses)</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              <strong>Important:</strong> This data is <strong>PUBLIC</strong> by nature of blockchain technology. Anyone can view it using a block explorer or the SkyMavis marketplace. We don&apos;t make it public—it already is.
            </p>

            <h3 className="text-xl font-medium mt-4 mb-2">2.2 Automatically Collected Information (Anonymous Analytics)</h3>
            <p className="text-muted-foreground leading-relaxed">
              When you access the Service, we may automatically collect minimal anonymous usage data:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Pages visited and features used</li>
              <li>Time and date of visits</li>
              <li>Browser type and device category (mobile vs desktop)</li>
              <li>Referring source (how you found us)</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              <strong>What we DON&apos;T collect:</strong> IP addresses, precise geolocation, device fingerprints, or cross-site tracking.
            </p>

            <h3 className="text-xl font-medium mt-4 mb-2">2.3 What We DON&apos;T Collect (Web3 Clarification)</h3>
            <div className="p-4 bg-gray-800/50 border border-gray-700 rounded mt-2">
              <p className="text-gray-300 leading-relaxed mb-3">
                🚫 <strong>Important clarifications</strong> (especially for Web3 users):
              </p>

              <p className="text-gray-300 leading-relaxed mt-3">
                <strong>NO wallet connection:</strong>
              </p>
              <ul className="list-disc list-inside text-gray-300 space-y-1">
                <li>We don&apos;t ask you to connect your wallet (no MetaMask, no Ronin Wallet)</li>
                <li>We don&apos;t see your wallet address unless it appears in public listings</li>
                <li>We NEVER ask for private keys or seed phrases</li>
                <li>We cannot access your funds or execute transactions</li>
              </ul>

              <p className="text-gray-300 leading-relaxed mt-3">
                <strong>NO personal information:</strong>
              </p>
              <ul className="list-disc list-inside text-gray-300 space-y-1">
                <li>No email required (beta phase has no accounts)</li>
                <li>No name, phone number, or address</li>
                <li>No KYC or identity verification</li>
              </ul>

              <p className="text-gray-300 leading-relaxed mt-3">
                <strong>NO sensitive tracking:</strong>
              </p>
              <ul className="list-disc list-inside text-gray-300 space-y-1">
                <li>No IP address logging or geolocation</li>
                <li>No device fingerprinting</li>
                <li>No cross-site tracking or third-party ad networks</li>
              </ul>
            </div>
            <p className="text-muted-foreground leading-relaxed mt-3">
              <strong>Why this matters:</strong> Many Web3 tools are scams that try to steal your keys. We&apos;re not one of them. AxiePro is 100% read-only—we can&apos;t touch your assets.
            </p>

            <h3 className="text-xl font-medium mt-4 mb-2">2.4 Cookies and Local Storage</h3>
            <p className="text-muted-foreground leading-relaxed">
              We may use minimal cookies or browser local storage to:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Remember your preferences (theme, view settings)</li>
              <li>Track anonymous usage for analytics</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-2">
              You can control cookies through your browser settings. Disabling cookies may limit some features of the Service, but core analytics functionality will still work.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. How We Use Your Information</h2>
            <p className="text-muted-foreground leading-relaxed">We use collected information to:</p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Provide and maintain the Service (display analytics, charts, insights)</li>
              <li>Analyze public blockchain data to calculate valuations and detect deals</li>
              <li>Analyze anonymous usage patterns to improve the Service</li>
              <li>Detect and prevent abuse (excessive requests, scraping attempts)</li>
              <li>Comply with legal obligations if required</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              <strong>What we DON&apos;T do with your data:</strong>
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>❌ Sell or share personal information with third parties</li>
              <li>❌ Use data for targeted advertising</li>
              <li>❌ Link wallet addresses to real-world identities</li>
              <li>❌ Share individual usage patterns (only aggregated analytics)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Understanding Blockchain Data</h2>
            <div className="p-4 bg-blue-900/20 border border-blue-800/30 rounded mb-4">
              <p className="text-blue-200 leading-relaxed">
                🔗 <strong>How we handle public blockchain data</strong>
              </p>
            </div>

            <h3 className="text-xl font-medium mt-4 mb-2">What is &quot;public blockchain data&quot;?</h3>
            <p className="text-muted-foreground leading-relaxed">
              Blockchain transactions on Ronin network are publicly visible to anyone. This includes:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Axie sales and transfers (prices, timestamps, parties involved)</li>
              <li>Marketplace listings (Axies for sale, their prices and attributes)</li>
              <li>NFT ownership (which wallet owns which Axie)</li>
              <li>Transaction history (publicly viewable on block explorers)</li>
            </ul>

            <h3 className="text-xl font-medium mt-4 mb-2">What we do with it:</h3>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              <li>Read sales history from Ronin blockchain and SkyMavis API</li>
              <li>Analyze marketplace listings to calculate floor prices and trends</li>
              <li>Calculate statistics (average prices, volume, market depth)</li>
              <li>Display analytics on AxiePro (charts, deal alerts, breeding probabilities)</li>
            </ul>

            <h3 className="text-xl font-medium mt-4 mb-2">What we DON&apos;T do:</h3>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              <li>❌ Store complete transaction histories in our database</li>
              <li>❌ Link wallet addresses to real identities (emails, names, etc.)</li>
              <li>❌ Share or sell blockchain data (it&apos;s already public)</li>
              <li>❌ Execute transactions or interact with wallets</li>
            </ul>

            <h3 className="text-xl font-medium mt-4 mb-2">GDPR & Blockchain Data:</h3>
            <p className="text-muted-foreground leading-relaxed">
              Wallet addresses are <strong>pseudonymous</strong> (not linked to your real name), but may be considered personal data under GDPR. However:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Public blockchain data is not subject to &quot;right to erasure&quot; (it&apos;s immutable)</li>
              <li>We process it under &quot;legitimate interest&quot; (public data analysis)</li>
              <li>We don&apos;t collect additional identifiers to link addresses to real people</li>
              <li>Our read-only approach minimizes privacy impact</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Legal Basis for Processing (GDPR)</h2>
            <p className="text-muted-foreground leading-relaxed">
              For users in the European Economic Area (EEA) and UK, we process your data under the following legal bases:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li><strong>Legitimate Interest:</strong> Analyzing public blockchain data for analytics purposes</li>
              <li><strong>Consent:</strong> For optional cookies and analytics (you can opt out)</li>
              <li><strong>Contractual Necessity:</strong> Providing the Service you requested (if you use our platform)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Data Sharing and Disclosure</h2>
            <p className="text-muted-foreground leading-relaxed">
              We do <strong>NOT</strong> sell your personal information. We may share information only in the following limited circumstances:
            </p>

            <h3 className="text-xl font-medium mt-4 mb-2">6.1 Service Providers</h3>
            <p className="text-muted-foreground leading-relaxed">
              Third-party vendors who assist in operating the Service:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li><strong>AWS (Amazon Web Services):</strong> Cloud hosting (us-west-2 region)</li>
              <li><strong>SkyMavis:</strong> GraphQL API for marketplace data (we READ from their API)</li>
              <li><strong>Analytics providers:</strong> Anonymous usage analytics (if implemented)</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-2">
              These providers have access only to data necessary to perform their functions and are obligated to protect it.
            </p>

            <h3 className="text-xl font-medium mt-4 mb-2">6.2 Legal Requirements</h3>
            <p className="text-muted-foreground leading-relaxed">
              We may disclose information if required by law or to:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Comply with legal processes (subpoenas, court orders)</li>
              <li>Protect our rights, property, or safety</li>
              <li>Prevent fraud or abuse of the Service</li>
            </ul>

            <h3 className="text-xl font-medium mt-4 mb-2">6.3 Aggregated Data</h3>
            <p className="text-muted-foreground leading-relaxed">
              We may share non-identifiable, aggregated statistics publicly:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>&quot;AxiePro users viewed 10,000 Axies this week&quot;</li>
              <li>&quot;Average floor price dropped 15% across all classes&quot;</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-2">
              This data cannot be traced back to individual users.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Third-Party Services</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service may integrate with or link to third-party services:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li><strong>SkyMavis GraphQL API:</strong> Axie Infinity marketplace data</li>
              <li><strong>Ronin Blockchain:</strong> On-chain transaction data</li>
              <li><strong>AWS:</strong> Cloud infrastructure</li>
              <li><strong>Axie Infinity Marketplace:</strong> External links to official marketplace</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              These services have their own privacy policies. We encourage you to review them. Notable:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li><strong>SkyMavis:</strong> <a href="https://skymavis.com/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">skymavis.com/privacy</a></li>
              <li><strong>AWS:</strong> <a href="https://aws.amazon.com/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">aws.amazon.com/privacy</a></li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Data Security</h2>
            <p className="text-muted-foreground leading-relaxed">
              We implement appropriate technical and organizational measures to protect your information:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>SSL/TLS encryption for data in transit (HTTPS)</li>
              <li>Secure cloud infrastructure (AWS with private VPCs)</li>
              <li>Database access restricted to application layer only</li>
              <li>Regular security assessments and updates</li>
              <li>Minimal data collection (reducing attack surface)</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              However, no method of transmission over the Internet is 100% secure. We cannot guarantee absolute security, but we follow industry best practices.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Data Retention</h2>
            <p className="text-muted-foreground leading-relaxed">
              We retain data only as long as necessary:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li><strong>Anonymous analytics:</strong> 24 months (for trend analysis)</li>
              <li><strong>Public blockchain data:</strong> Not stored permanently (we READ from APIs as needed)</li>
              <li><strong>Aggregated statistics:</strong> Retained indefinitely (non-identifiable)</li>
              <li><strong>Cookies:</strong> Per your browser settings (typically 1 year or until cleared)</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              When the retention period expires, we securely delete or anonymize data, unless required by law to retain it longer.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Your Rights (GDPR & Privacy)</h2>
            <p className="text-muted-foreground leading-relaxed">
              Depending on your location (especially EEA/UK), you may have the following rights:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li><strong>Access:</strong> Request a copy of your personal data (contact us at contact@axiepro.io)</li>
              <li><strong>Correction:</strong> Request correction of inaccurate data</li>
              <li><strong>Deletion:</strong> Request deletion of your data (limited—see below)</li>
              <li><strong>Opt-out:</strong> Disable cookies or analytics tracking</li>
              <li><strong>Portability:</strong> Request your data in a portable format</li>
              <li><strong>Object:</strong> Object to processing based on legitimate interest</li>
            </ul>

            <h3 className="text-xl font-medium mt-4 mb-2">Limitations on Deletion:</h3>
            <div className="p-4 bg-yellow-900/20 border border-yellow-800/30 rounded mt-2">
              <p className="text-yellow-200 leading-relaxed">
                ⚠️ <strong>Important:</strong> Public blockchain data is <strong>immutable</strong>. We cannot delete:
              </p>
              <ul className="list-disc list-inside text-yellow-200 mt-2 space-y-1">
                <li>Transactions recorded on Ronin blockchain</li>
                <li>Marketplace listings from SkyMavis API (they control this data)</li>
                <li>NFT ownership records (publicly visible on-chain)</li>
              </ul>
              <p className="text-yellow-200 leading-relaxed mt-2">
                We <strong>can</strong> delete: Your usage analytics, cookies, or any preferences stored in our database (if you had an account).
              </p>
            </div>

            <p className="text-muted-foreground leading-relaxed mt-4">
              To exercise these rights, please contact us at <a href="mailto:contact@axiepro.io" className="text-primary hover:underline">contact@axiepro.io</a>.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. International Data Transfers</h2>
            <p className="text-muted-foreground leading-relaxed">
              Your information may be transferred to and processed in the United States (AWS us-west-2 region). We ensure appropriate safeguards are in place:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>AWS complies with GDPR and provides Standard Contractual Clauses (SCCs)</li>
              <li>Data is encrypted in transit and at rest</li>
              <li>Minimal personal data is collected (reducing transfer risks)</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              By using AxiePro, you acknowledge that your data may be processed in the United States.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. Children&apos;s Privacy</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service is not intended for children under 13 years of age (16 in the EEA). We do not knowingly collect personal information from children. If we become aware that we have collected such information, we will take steps to delete it promptly.
            </p>
            <p className="text-muted-foreground leading-relaxed mt-3">
              If you believe a child has provided us with personal information, please contact us at contact@axiepro.io.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">13. Changes to This Policy</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may update this Privacy Policy from time to time. We will notify you of any changes by:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>Posting the new Privacy Policy on this page</li>
              <li>Updating the &quot;Last updated&quot; date at the top</li>
              <li>Displaying a banner notification on the site (for material changes)</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              Your continued use of the Service after changes constitutes acceptance of the updated policy. We encourage you to review this policy periodically.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">14. Contact Us</h2>
            <p className="text-muted-foreground leading-relaxed">
              If you have any questions about this Privacy Policy, our data practices, or wish to exercise your privacy rights, please contact us at:
            </p>
            <p className="text-muted-foreground mt-2">
              Email: <a href="mailto:contact@axiepro.io" className="text-primary hover:underline">contact@axiepro.io</a>
            </p>
            <p className="text-muted-foreground mt-3">
              We will respond to your inquiry within 30 days (as required by GDPR).
            </p>
          </section>

          {/* Transparency Statement */}
          <section className="bg-green-900/20 p-6 rounded-lg border border-green-800/30">
            <h2 className="text-xl font-semibold mb-3">Our Privacy Commitment</h2>
            <p className="text-muted-foreground leading-relaxed">
              AxiePro is built with privacy in mind from the ground up:
            </p>
            <ul className="list-disc list-inside text-muted-foreground mt-2 space-y-1">
              <li>✅ No wallet connection = Can&apos;t access your funds</li>
              <li>✅ No personal data collection = Nothing to leak or sell</li>
              <li>✅ Read-only analytics = Minimal privacy footprint</li>
              <li>✅ Public data only = Analyzing what&apos;s already public</li>
              <li>✅ Transparent policies = No hidden clauses</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-3">
              We believe in building trust through transparency. If something in this policy is unclear, or if you have privacy concerns, please reach out. We&apos;re here to help.
            </p>
          </section>
        </CardContent>
      </Card>
    </div>
  );
}
