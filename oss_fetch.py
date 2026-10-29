"""Company-backed open-source projects by language: GitHub repo/org info, PR activity, community channels.

Candidates are hand-picked (backer + careers page); the script keeps only repos whose GitHub primary
language matches, ranks by stars, and checks every careers URL actually loads.
Usage: python -I oss_fetch.py
"""
import base64
import datetime
import json
import re
import urllib.parse
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # -I drops the script dir
from fetch import GH, OUT, classify, get, host, log, pmap  # noqa: E402

# (repo, backer, backer site, careers page)
CANDIDATES = {
    "Go": {"langs": {"Go"}, "top": 60, "repos": [
        ("golang/go", "Google", "https://go.dev", "https://careers.google.com"),
        ("grpc/grpc-go", "Google", "https://grpc.io", "https://careers.google.com"),
        ("grafana/mimir", "Grafana Labs", "https://grafana.com", "https://grafana.com/about/careers/"),
        ("grafana/tempo", "Grafana Labs", "https://grafana.com", "https://grafana.com/about/careers/"),
        ("hashicorp/consul", "HashiCorp (IBM)", "https://www.hashicorp.com", "https://www.hashicorp.com/careers"),
        ("hashicorp/nomad", "HashiCorp (IBM)", "https://www.hashicorp.com", "https://www.hashicorp.com/careers"),
        ("hashicorp/packer", "HashiCorp (IBM)", "https://www.hashicorp.com", "https://www.hashicorp.com/careers"),
        ("authzed/spicedb", "AuthZed", "https://authzed.com", "https://authzed.com/careers"),
        ("crossplane/crossplane", "Upbound", "https://www.upbound.io", "https://www.upbound.io/careers"),
        ("kyverno/kyverno", "Nirmata", "https://nirmata.com", "https://nirmata.com/careers/"),
        ("loft-sh/vcluster", "vCluster Labs", "https://www.vcluster.com", None),
        ("rudderlabs/rudder-server", "RudderStack", "https://www.rudderstack.com", "https://www.rudderstack.com/careers/"),
        ("jetify-com/devbox", "Jetify", "https://www.jetify.com", "https://www.jetify.com/careers"),
        ("charmbracelet/bubbletea", "Charm", "https://charm.sh", None),
        ("k3s-io/k3s", "SUSE", "https://www.suse.com", "https://www.suse.com/company/careers/"),
        ("rancher/rancher", "SUSE", "https://www.suse.com", "https://www.suse.com/company/careers/"),
        ("portainer/portainer", "Portainer", "https://www.portainer.io", "https://www.portainer.io/careers"),
        ("netbirdio/netbird", "NetBird", "https://netbird.io", "https://netbird.io/careers"),
        ("smallstep/certificates", "Smallstep", "https://smallstep.com", "https://smallstep.com/careers"),
        ("harness/harness", "Harness", "https://www.harness.io", "https://www.harness.io/company/careers"),
        ("argoproj/argo-cd", "Akuity / Intuit", "https://akuity.io", "https://akuity.io/careers"),
        ("cloudflare/cloudflared", "Cloudflare", "https://www.cloudflare.com", "https://www.cloudflare.com/careers/"),
        ("uber-go/zap", "Uber", "https://www.uber.com", "https://www.uber.com/careers"),
        ("stripe/stripe-cli", "Stripe", "https://stripe.com", "https://stripe.com/jobs"),
        ("hashicorp/terraform", "HashiCorp (IBM)", "https://www.hashicorp.com", "https://www.hashicorp.com/careers"),
        ("hashicorp/vault", "HashiCorp (IBM)", "https://www.hashicorp.com", "https://www.hashicorp.com/careers"),
        ("grafana/loki", "Grafana Labs", "https://grafana.com", "https://grafana.com/about/careers/"),
        ("grafana/k6", "Grafana Labs", "https://grafana.com", "https://grafana.com/about/careers/"),
        ("cockroachdb/cockroach", "Cockroach Labs", "https://www.cockroachlabs.com", "https://www.cockroachlabs.com/careers/"),
        ("moby/moby", "Docker", "https://www.docker.com", "https://www.docker.com/careers/"),
        ("docker/compose", "Docker", "https://www.docker.com", "https://www.docker.com/careers/"),
        ("pingcap/tidb", "PingCAP", "https://www.pingcap.com", "https://www.pingcap.com/careers/"),
        ("temporalio/temporal", "Temporal Technologies", "https://temporal.io", "https://temporal.io/careers"),
        ("tailscale/tailscale", "Tailscale", "https://tailscale.com", "https://tailscale.com/careers"),
        ("cilium/cilium", "Isovalent (Cisco)", "https://isovalent.com", "https://isovalent.com/careers/"),
        ("minio/minio", "MinIO", "https://min.io", "https://min.io/careers"),
        ("influxdata/telegraf", "InfluxData", "https://www.influxdata.com", "https://www.influxdata.com/careers/"),
        ("pulumi/pulumi", "Pulumi", "https://www.pulumi.com", "https://www.pulumi.com/careers/"),
        ("gravitational/teleport", "Teleport", "https://goteleport.com", "https://goteleport.com/careers/"),
        ("traefik/traefik", "Traefik Labs", "https://traefik.io", "https://traefik.io/careers/"),
        ("vitessio/vitess", "PlanetScale", "https://planetscale.com", "https://planetscale.com/careers"),
        ("coder/coder", "Coder", "https://coder.com", "https://coder.com/careers"),
        ("dagger/dagger", "Dagger", "https://dagger.io", "https://dagger.io/careers"),
        ("supabase/auth", "Supabase", "https://supabase.com", "https://supabase.com/careers"),
        ("ollama/ollama", "Ollama", "https://ollama.com", None),
        ("linkerd/linkerd2", "Buoyant", "https://buoyant.io", "https://buoyant.io/careers"),
        ("nats-io/nats-server", "Synadia", "https://www.synadia.com", "https://www.synadia.com/careers"),
        ("ory/kratos", "Ory", "https://www.ory.sh", "https://www.ory.sh/jobs"),
        ("livekit/livekit", "LiveKit", "https://livekit.io", "https://livekit.io/careers"),
        ("mattermost/mattermost", "Mattermost", "https://mattermost.com", "https://mattermost.com/careers/"),
        ("containers/podman", "Red Hat", "https://www.redhat.com", "https://www.redhat.com/en/jobs"),
        ("zitadel/zitadel", "ZITADEL", "https://zitadel.com", "https://zitadel.com/careers"),
        ("weaviate/weaviate", "Weaviate", "https://weaviate.io", "https://weaviate.io/company/careers"),
        ("milvus-io/milvus", "Zilliz", "https://zilliz.com", "https://zilliz.com/careers"),
        ("aquasecurity/trivy", "Aqua Security", "https://www.aquasec.com", "https://www.aquasec.com/about-us/careers/"),
        ("redpanda-data/connect", "Redpanda", "https://www.redpanda.com", "https://www.redpanda.com/careers"),
        ("kubernetes/kubernetes", "Google (CNCF)", "https://kubernetes.io", "https://careers.google.com"),
        ("microsoft/TypeScript", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("microsoft/typescript-go", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("google/gvisor", "Google", "https://gvisor.dev", "https://careers.google.com"),
        ("cli/cli", "GitHub", "https://github.com", "https://www.github.careers"),
        ("grafana/alloy", "Grafana Labs", "https://grafana.com", "https://grafana.com/about/careers/"),
        ("grafana/pyroscope", "Grafana Labs", "https://grafana.com", "https://grafana.com/about/careers/"),
        ("hashicorp/boundary", "HashiCorp (IBM)", "https://www.hashicorp.com", "https://www.hashicorp.com/careers"),
        ("cloudflare/cfssl", "Cloudflare", "https://www.cloudflare.com", "https://www.cloudflare.com/careers/"),
        ("DataDog/datadog-agent", "Datadog", "https://www.datadoghq.com", "https://careers.datadoghq.com"),
        ("elastic/beats", "Elastic", "https://www.elastic.co", "https://www.elastic.co/careers"),
        ("uber/cadence", "Uber", "https://www.uber.com", "https://www.uber.com/careers"),
        ("uber-go/fx", "Uber", "https://www.uber.com", "https://www.uber.com/careers"),
        ("cloudwego/kitex", "ByteDance", "https://www.cloudwego.io", "https://jobs.bytedance.com/en"),
        ("cloudwego/hertz", "ByteDance", "https://www.cloudwego.io", "https://jobs.bytedance.com/en"),
        ("aws/karpenter-provider-aws", "AWS", "https://aws.amazon.com", "https://www.amazon.jobs"),
        ("aws/aws-sdk-go-v2", "AWS", "https://aws.amazon.com", "https://www.amazon.jobs"),
        ("digitalocean/doctl", "DigitalOcean", "https://www.digitalocean.com", "https://www.digitalocean.com/careers"),
        ("superfly/flyctl", "Fly.io", "https://fly.io", "https://fly.io/jobs/"),
        ("go-gitea/gitea", "CommitGo", "https://about.gitea.com", None),
        ("dapr/dapr", "Diagrid", "https://www.diagrid.io", "https://www.diagrid.io/careers"),
        ("openfga/openfga", "Okta", "https://www.okta.com", "https://www.okta.com/company/careers/"),
        ("anchore/syft", "Anchore", "https://anchore.com", "https://anchore.com/careers/"),
        ("anchore/grype", "Anchore", "https://anchore.com", "https://anchore.com/careers/"),
        ("cert-manager/cert-manager", "CyberArk (Venafi)", "https://www.cyberark.com", "https://www.cyberark.com/careers/"),
        ("goharbor/harbor", "Broadcom (VMware)", "https://www.broadcom.com", "https://www.broadcom.com/company/careers"),
        ("vmware-tanzu/velero", "Broadcom (VMware)", "https://www.broadcom.com", "https://www.broadcom.com/company/careers"),
        ("akuity/kargo", "Akuity", "https://akuity.io", "https://akuity.io/careers"),
        ("kubescape/kubescape", "ARMO", "https://www.armosec.io", "https://www.armosec.io/careers/"),
        ("gruntwork-io/terragrunt", "Gruntwork", "https://www.gruntwork.io", "https://www.gruntwork.io/careers"),
        ("infracost/infracost", "Infracost", "https://www.infracost.io", "https://www.infracost.io/join-the-team/"),
        ("hatchet-dev/hatchet", "Hatchet", "https://hatchet.run", None),
        ("ariga/atlas", "Ariga", "https://atlasgo.io", None),
        ("encoredev/encore", "Encore", "https://encore.dev", "https://encore.dev/careers"),
        ("openziti/ziti", "NetFoundry", "https://netfoundry.io", "https://netfoundry.io/careers/"),
        ("projectdiscovery/nuclei", "ProjectDiscovery", "https://projectdiscovery.io", None),
        ("trufflesecurity/trufflehog", "Truffle Security", "https://trufflesecurity.com", "https://trufflesecurity.com/careers"),
        ("dolthub/dolt", "DoltHub", "https://www.dolthub.com", "https://www.dolthub.com/careers"),
        ("juicedata/juicefs", "Juicedata", "https://juicefs.com", None),
        ("photoprism/photoprism", "PhotoPrism", "https://www.photoprism.app", None),
        ("SigNoz/signoz", "SigNoz", "https://signoz.io", "https://signoz.io/careers/"),
        ("openmeterio/openmeter", "Kong (OpenMeter)", "https://konghq.com", "https://konghq.com/careers"),
    ]},
    "JavaScript / TypeScript": {"langs": {"JavaScript", "TypeScript"}, "top": 70, "repos": [
        ("microsoft/TypeScript", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("microsoft/playwright", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("angular/angular", "Google", "https://angular.dev", "https://careers.google.com"),
        ("puppeteer/puppeteer", "Google", "https://pptr.dev", "https://careers.google.com"),
        ("facebook/docusaurus", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("facebook/lexical", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("vitejs/vite", "VoidZero", "https://voidzero.dev", None),
        ("vitest-dev/vitest", "VoidZero", "https://voidzero.dev", None),
        ("withastro/astro", "Astro", "https://astro.build", None),
        ("expo/expo", "Expo", "https://expo.dev", "https://expo.dev/careers"),
        ("vercel/ai", "Vercel", "https://vercel.com", "https://vercel.com/careers"),
        ("shadcn-ui/ui", "Vercel", "https://vercel.com", "https://vercel.com/careers"),
        ("appwrite/appwrite", "Appwrite", "https://appwrite.io", "https://appwrite.io/careers"),
        ("refinedev/refine", "Refine", "https://refine.dev", "https://refine.dev/careers/"),
        ("lobehub/lobe-chat", "LobeHub", "https://lobehub.com", None),
        ("langgenius/dify", "LangGenius", "https://dify.ai", None),
        ("Infisical/infisical", "Infisical", "https://infisical.com", "https://infisical.com/careers"),
        ("dubinc/dub", "Dub", "https://dub.co", "https://dub.co/careers"),
        ("umami-software/umami", "Umami Software", "https://umami.is", None),
        ("hcengineering/platform", "Huly", "https://huly.io", None),
        ("RocketChat/Rocket.Chat", "Rocket.Chat", "https://www.rocket.chat", "https://www.rocket.chat/careers"),
        ("mattermost/mattermost", "Mattermost", "https://mattermost.com", "https://mattermost.com/careers/"),
        ("elastic/kibana", "Elastic", "https://www.elastic.co", "https://www.elastic.co/careers"),
        ("TryGhost/Ghost", "Ghost Foundation", "https://ghost.org", "https://careers.ghost.org"),
        ("mermaid-js/mermaid", "Mermaid Chart", "https://www.mermaidchart.com", None),
        ("xyflow/xyflow", "xyflow", "https://xyflow.com", None),
        ("ueberdosis/tiptap", "Tiptap", "https://tiptap.dev", "https://tiptap.dev/jobs"),
        ("Kong/insomnia", "Kong", "https://konghq.com", "https://konghq.com/careers"),
        ("getsentry/sentry-javascript", "Sentry", "https://sentry.io", "https://sentry.io/careers/"),
        ("cypress-io/cypress", "Cypress", "https://www.cypress.io", "https://www.cypress.io/careers"),
        ("vercel/next.js", "Vercel", "https://vercel.com", "https://vercel.com/careers"),
        ("facebook/react", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("microsoft/vscode", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("supabase/supabase", "Supabase", "https://supabase.com", "https://supabase.com/careers"),
        ("n8n-io/n8n", "n8n", "https://n8n.io", "https://n8n.io/careers/"),
        ("strapi/strapi", "Strapi", "https://strapi.io", "https://strapi.io/careers"),
        ("directus/directus", "Directus", "https://directus.io", "https://directus.io/careers"),
        ("calcom/cal.com", "Cal.com", "https://cal.com", "https://cal.com/jobs"),
        ("twentyhq/twenty", "Twenty", "https://twenty.com", "https://twenty.com/jobs"),
        ("novuhq/novu", "Novu", "https://novu.co", "https://novu.co/careers"),
        ("mui/material-ui", "MUI", "https://mui.com", "https://mui.com/careers/"),
        ("storybookjs/storybook", "Chromatic", "https://www.chromatic.com", "https://www.chromatic.com/company/jobs"),
        ("remix-run/react-router", "Shopify", "https://www.shopify.com", "https://www.shopify.com/careers"),
        ("prisma/prisma", "Prisma", "https://www.prisma.io", "https://www.prisma.io/careers"),
        ("payloadcms/payload", "Payload (Figma)", "https://payloadcms.com", None),
        ("medusajs/medusa", "Medusa", "https://medusajs.com", "https://medusajs.com/careers/"),
        ("hoppscotch/hoppscotch", "Hoppscotch", "https://hoppscotch.com", "https://hoppscotch.com/careers"),
        ("excalidraw/excalidraw", "Excalidraw", "https://plus.excalidraw.com", None),
        ("tldraw/tldraw", "tldraw", "https://tldraw.dev", "https://tldraw.dev/careers"),
        ("documenso/documenso", "Documenso", "https://documenso.com", "https://documenso.com/careers"),
        ("triggerdotdev/trigger.dev", "Trigger.dev", "https://trigger.dev", "https://trigger.dev/careers"),
        ("langchain-ai/langchainjs", "LangChain", "https://www.langchain.com", "https://www.langchain.com/careers"),
        ("grafana/grafana", "Grafana Labs", "https://grafana.com", "https://grafana.com/about/careers/"),
        ("appsmithorg/appsmith", "Appsmith", "https://www.appsmith.com", "https://www.appsmith.com/careers"),
        ("ToolJet/ToolJet", "ToolJet", "https://www.tooljet.com", "https://www.tooljet.com/careers"),
        ("nocodb/nocodb", "NocoDB", "https://nocodb.com", "https://nocodb.com/careers"),
        ("immich-app/immich", "FUTO", "https://futo.org", "https://futo.org/jobs/"),
        ("formbricks/formbricks", "Formbricks", "https://formbricks.com", "https://formbricks.com/careers"),
        ("outline/outline", "General Outline", "https://www.getoutline.com", None),
        ("facebook/react-native", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("google-gemini/gemini-cli", "Google", "https://ai.google.dev", "https://careers.google.com"),
        ("google/zx", "Google", "https://google.github.io/zx/", "https://careers.google.com"),
        ("google/blockly", "Google", "https://developers.google.com/blockly", "https://careers.google.com"),
        ("GoogleChrome/lighthouse", "Google", "https://developer.chrome.com", "https://careers.google.com"),
        ("openai/openai-node", "OpenAI", "https://openai.com", "https://openai.com/careers"),
        ("aws/aws-cdk", "AWS", "https://aws.amazon.com", "https://www.amazon.jobs"),
        ("backstage/backstage", "Spotify", "https://www.spotify.com", "https://www.lifeatspotify.com"),
        ("WordPress/gutenberg", "Automattic", "https://automattic.com", "https://automattic.com/work-with-us/"),
        ("mozilla/pdf.js", "Mozilla", "https://www.mozilla.org", "https://www.mozilla.org/en-US/careers/"),
        ("sveltejs/svelte", "Vercel", "https://vercel.com", "https://vercel.com/careers"),
        ("sveltejs/kit", "Vercel", "https://vercel.com", "https://vercel.com/careers"),
        ("nuxt/nuxt", "Vercel (NuxtLabs)", "https://vercel.com", "https://vercel.com/careers"),
        ("vercel/swr", "Vercel", "https://vercel.com", "https://vercel.com/careers"),
        ("denoland/fresh", "Deno", "https://deno.com", "https://deno.com/jobs"),
        ("QwikDev/qwik", "Builder.io", "https://www.builder.io", "https://www.builder.io/m/careers"),
        ("netlify/cli", "Netlify", "https://www.netlify.com", "https://www.netlify.com/careers/"),
        ("cloudflare/workers-sdk", "Cloudflare", "https://www.cloudflare.com", "https://www.cloudflare.com/careers/"),
        ("Shopify/hydrogen", "Shopify", "https://www.shopify.com", "https://www.shopify.com/careers"),
        ("ionic-team/ionic-framework", "Ionic (OutSystems)", "https://ionic.io", "https://www.outsystems.com/company/careers/"),
        ("ionic-team/capacitor", "Ionic (OutSystems)", "https://ionic.io", "https://www.outsystems.com/company/careers/"),
        ("serverless/serverless", "Serverless Inc.", "https://www.serverless.com", None),
        ("apollographql/apollo-client", "Apollo GraphQL", "https://www.apollographql.com", "https://www.apollographql.com/careers"),
        ("mongodb/node-mongodb-native", "MongoDB", "https://www.mongodb.com", "https://www.mongodb.com/company/careers"),
        ("drizzle-team/drizzle-orm", "Drizzle Team", "https://orm.drizzle.team", None),
        ("better-auth/better-auth", "Better Auth", "https://www.better-auth.com", None),
        ("clerk/javascript", "Clerk", "https://clerk.com", "https://clerk.com/careers"),
        ("resend/react-email", "Resend", "https://resend.com", "https://resend.com/careers"),
        ("mastra-ai/mastra", "Mastra", "https://mastra.ai", None),
        ("langfuse/langfuse", "Langfuse", "https://langfuse.com", "https://langfuse.com/careers"),
        ("FlowiseAI/Flowise", "FlowiseAI (Workday)", "https://flowiseai.com", None),
        ("activepieces/activepieces", "Activepieces", "https://www.activepieces.com", None),
        ("makeplane/plane", "Plane", "https://plane.so", "https://plane.so/careers"),
        ("toeverything/AFFiNE", "Toeverything", "https://affine.pro", None),
        ("budibase/budibase", "Budibase", "https://budibase.com", "https://budibase.com/careers/"),
        ("sanity-io/sanity", "Sanity", "https://www.sanity.io", "https://www.sanity.io/careers"),
        ("vendure-ecommerce/vendure", "Vendure", "https://vendure.io", None),
        ("logto-io/logto", "Silverhand (Logto)", "https://logto.io", None),
        ("unkeyed/unkey", "Unkey", "https://www.unkey.com", None),
        ("jitsi/jitsi-meet", "8x8", "https://www.8x8.com", "https://www.8x8.com/company/careers"),
        ("element-hq/element-web", "Element", "https://element.io", "https://element.io/careers"),
        ("highlight/highlight", "LaunchDarkly (Highlight)", "https://launchdarkly.com", "https://launchdarkly.com/careers/"),
        ("lightdash/lightdash", "Lightdash", "https://www.lightdash.com", None),
        ("openreplay/openreplay", "OpenReplay", "https://openreplay.com", None),
    ]},
    "Python": {"langs": {"Python"}, "top": 55, "repos": [
        ("langgenius/dify", "LangGenius", "https://dify.ai", None),
        ("open-webui/open-webui", "Open WebUI", "https://openwebui.com", None),
        ("ansible/ansible", "Red Hat", "https://www.redhat.com", "https://www.redhat.com/en/jobs"),
        ("apache/superset", "Preset", "https://preset.io", "https://preset.io/careers/"),
        ("openai/openai-python", "OpenAI", "https://openai.com", "https://openai.com/careers"),
        ("microsoft/autogen", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("microsoft/markitdown", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("jax-ml/jax", "Google", "https://docs.jax.dev", "https://careers.google.com"),
        ("keras-team/keras", "Google", "https://keras.io", "https://careers.google.com"),
        ("scikit-learn/scikit-learn", ":probabl.", "https://probabl.ai", None),
        ("wandb/wandb", "Weights & Biases (CoreWeave)", "https://wandb.ai", "https://wandb.ai/site/careers"),
        ("ultralytics/ultralytics", "Ultralytics", "https://www.ultralytics.com", "https://www.ultralytics.com/careers"),
        ("deepset-ai/haystack", "deepset", "https://www.deepset.ai", "https://www.deepset.ai/careers"),
        ("unslothai/unsloth", "Unsloth AI", "https://unsloth.ai", None),
        ("pydantic/pydantic-ai", "Pydantic", "https://pydantic.dev", "https://pydantic.dev/jobs"),
        ("Lightning-AI/pytorch-lightning", "Lightning AI", "https://lightning.ai", "https://lightning.ai/careers"),
        ("netbox-community/netbox", "NetBox Labs", "https://netboxlabs.com", "https://netboxlabs.com/careers/"),
        ("frappe/erpnext", "Frappe", "https://frappe.io", "https://frappe.io/careers"),
        ("odoo/odoo", "Odoo", "https://www.odoo.com", "https://www.odoo.com/jobs"),
        ("saleor/saleor", "Saleor", "https://saleor.io", "https://saleor.io/careers"),
        ("HumanSignal/label-studio", "HumanSignal", "https://humansignal.com", "https://humansignal.com/careers/"),
        ("airbytehq/airbyte", "Airbyte", "https://airbyte.com", "https://airbyte.com/careers"),
        ("chroma-core/chroma", "Chroma", "https://www.trychroma.com", "https://www.trychroma.com/careers"),
        ("vllm-project/vllm", "Red Hat (Neural Magic)", "https://www.redhat.com", "https://www.redhat.com/en/jobs"),
        ("huggingface/transformers", "Hugging Face", "https://huggingface.co", "https://apply.workable.com/huggingface/"),
        ("langchain-ai/langchain", "LangChain", "https://www.langchain.com", "https://www.langchain.com/careers"),
        ("pytorch/pytorch", "Meta / PyTorch Foundation", "https://pytorch.org", "https://www.metacareers.com"),
        ("home-assistant/core", "Nabu Casa", "https://www.nabucasa.com", "https://www.nabucasa.com/careers/"),
        ("apache/airflow", "Astronomer", "https://www.astronomer.io", "https://www.astronomer.io/careers/"),
        ("ray-project/ray", "Anyscale", "https://www.anyscale.com", "https://www.anyscale.com/careers"),
        ("PostHog/posthog", "PostHog", "https://posthog.com", "https://posthog.com/careers"),
        ("gradio-app/gradio", "Hugging Face", "https://huggingface.co", "https://apply.workable.com/huggingface/"),
        ("streamlit/streamlit", "Snowflake", "https://www.snowflake.com", "https://careers.snowflake.com"),
        ("dagster-io/dagster", "Dagster Labs", "https://dagster.io", "https://dagster.io/careers"),
        ("PrefectHQ/prefect", "Prefect", "https://www.prefect.io", "https://www.prefect.io/careers"),
        ("getsentry/sentry", "Sentry", "https://sentry.io", "https://sentry.io/careers/"),
        ("zulip/zulip", "Kandra Labs", "https://zulip.com", "https://zulip.com/jobs/"),
        ("run-llama/llama_index", "LlamaIndex", "https://www.llamaindex.ai", "https://www.llamaindex.ai/careers"),
        ("mlflow/mlflow", "Databricks", "https://www.databricks.com", "https://www.databricks.com/company/careers"),
        ("pydantic/pydantic", "Pydantic", "https://pydantic.dev", "https://pydantic.dev/jobs"),
        ("Significant-Gravitas/AutoGPT", "AutoGPT", "https://agpt.co", None),
        ("crewAIInc/crewAI", "crewAI", "https://www.crewai.com", "https://www.crewai.com/careers"),
        ("browser-use/browser-use", "Browser Use", "https://browser-use.com", None),
        ("openai/whisper", "OpenAI", "https://openai.com", "https://openai.com/careers"),
        ("openai/openai-agents-python", "OpenAI", "https://openai.com", "https://openai.com/careers"),
        ("google/adk-python", "Google", "https://google.github.io/adk-docs/", "https://careers.google.com"),
        ("facebookresearch/detectron2", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("microsoft/DeepSpeed", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("microsoft/graphrag", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("microsoft/qlib", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("NVIDIA/NeMo", "NVIDIA", "https://www.nvidia.com", "https://www.nvidia.com/en-us/about-nvidia/careers/"),
        ("NVIDIA/Megatron-LM", "NVIDIA", "https://www.nvidia.com", "https://www.nvidia.com/en-us/about-nvidia/careers/"),
        ("huggingface/diffusers", "Hugging Face", "https://huggingface.co", "https://apply.workable.com/huggingface/"),
        ("huggingface/peft", "Hugging Face", "https://huggingface.co", "https://apply.workable.com/huggingface/"),
        ("huggingface/trl", "Hugging Face", "https://huggingface.co", "https://apply.workable.com/huggingface/"),
        ("langchain-ai/langgraph", "LangChain", "https://www.langchain.com", "https://www.langchain.com/careers"),
        ("comfyanonymous/ComfyUI", "Comfy Org", "https://www.comfy.org", "https://www.comfy.org/careers"),
        ("infiniflow/ragflow", "InfiniFlow", "https://ragflow.io", None),
        ("mem0ai/mem0", "Mem0", "https://mem0.ai", None),
        ("agno-agi/agno", "Agno", "https://www.agno.com", None),
        ("langflow-ai/langflow", "DataStax (IBM)", "https://www.datastax.com", "https://www.datastax.com/company/careers"),
        ("dbt-labs/dbt-core", "dbt Labs", "https://www.getdbt.com", "https://www.getdbt.com/careers"),
        ("great-expectations/great_expectations", "GX", "https://greatexpectations.io", "https://greatexpectations.io/careers"),
        ("plotly/plotly.py", "Plotly", "https://plotly.com", "https://plotly.com/careers/"),
        ("plotly/dash", "Plotly", "https://plotly.com", "https://plotly.com/careers/"),
        ("marimo-team/marimo", "marimo", "https://marimo.io", "https://marimo.io/careers"),
        ("reflex-dev/reflex", "Reflex", "https://reflex.dev", "https://reflex.dev/careers"),
        ("goauthentik/authentik", "Authentik Security", "https://goauthentik.io", None),
        ("saltstack/salt", "Broadcom (VMware)", "https://www.broadcom.com", "https://www.broadcom.com/company/careers"),
        ("scrapy/scrapy", "Zyte", "https://www.zyte.com", "https://www.zyte.com/jobs/"),
        ("frappe/frappe", "Frappe", "https://frappe.io", "https://frappe.io/careers"),
        ("wagtail/wagtail", "Torchbox", "https://torchbox.com", "https://torchbox.com/careers/"),
        ("bentoml/BentoML", "BentoML", "https://www.bentoml.com", None),
        ("skypilot-org/skypilot", "SkyPilot", "https://skypilot.co", None),
        ("explosion/spaCy", "Explosion", "https://explosion.ai", None),
        ("RasaHQ/rasa", "Rasa", "https://rasa.com", "https://rasa.com/careers/"),
        ("zenml-io/zenml", "ZenML", "https://www.zenml.io", "https://www.zenml.io/careers"),
        ("evidentlyai/evidently", "Evidently AI", "https://www.evidentlyai.com", None),
        ("Arize-ai/phoenix", "Arize AI", "https://arize.com", "https://arize.com/careers/"),
    ]},
    "Rust": {"langs": {"Rust"}, "top": 35, "repos": [
        ("vercel/turborepo", "Vercel", "https://vercel.com", "https://vercel.com/careers"),
        ("oxc-project/oxc", "VoidZero", "https://voidzero.dev", None),
        ("rolldown/rolldown", "VoidZero", "https://voidzero.dev", None),
        ("astral-sh/ty", "Astral", "https://astral.sh", "https://astral.sh/careers"),
        ("openai/codex", "OpenAI", "https://openai.com", "https://openai.com/careers"),
        ("facebook/pyrefly", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("cloudflare/pingora", "Cloudflare", "https://www.cloudflare.com", "https://www.cloudflare.com/careers/"),
        ("firecracker-microvm/firecracker", "AWS", "https://aws.amazon.com", "https://www.amazon.jobs"),
        ("bottlerocket-os/bottlerocket", "AWS", "https://aws.amazon.com", "https://www.amazon.jobs"),
        ("tikv/tikv", "PingCAP", "https://www.pingcap.com", "https://www.pingcap.com/careers/"),
        ("risingwavelabs/risingwave", "RisingWave Labs", "https://risingwave.com", None),
        ("databendlabs/databend", "Databend Labs", "https://www.databend.com", None),
        ("paradedb/paradedb", "ParadeDB", "https://www.paradedb.com", "https://www.paradedb.com/careers"),
        ("neondatabase/neon", "Databricks (Neon)", "https://neon.com", "https://www.databricks.com/company/careers"),
        ("quickwit-oss/tantivy", "Datadog (Quickwit)", "https://quickwit.io", "https://careers.datadoghq.com"),
        ("lancedb/lancedb", "LanceDB", "https://lancedb.com", None),
        ("GreptimeTeam/greptimedb", "Greptime", "https://greptime.com", None),
        ("prefix-dev/pixi", "prefix.dev", "https://prefix.dev", None),
        ("typst/typst", "Typst GmbH", "https://typst.app", None),
        ("juspay/hyperswitch", "Juspay", "https://juspay.io", "https://juspay.io/careers"),
        ("slint-ui/slint", "SixtyFPS", "https://slint.dev", None),
        ("DioxusLabs/dioxus", "Dioxus Labs", "https://dioxuslabs.com", None),
        ("wasmerio/wasmer", "Wasmer", "https://wasmer.io", None),
        ("denoland/deno", "Deno", "https://deno.com", "https://deno.com/jobs"),
        ("astral-sh/ruff", "Astral", "https://astral.sh", "https://astral.sh/careers"),
        ("astral-sh/uv", "Astral", "https://astral.sh", "https://astral.sh/careers"),
        ("tauri-apps/tauri", "CrabNebula", "https://crabnebula.dev", "https://crabnebula.dev/careers"),
        ("zed-industries/zed", "Zed Industries", "https://zed.dev", "https://zed.dev/jobs"),
        ("meilisearch/meilisearch", "Meilisearch", "https://www.meilisearch.com", "https://www.meilisearch.com/careers"),
        ("qdrant/qdrant", "Qdrant", "https://qdrant.tech", "https://qdrant.tech/careers/"),
        ("surrealdb/surrealdb", "SurrealDB", "https://surrealdb.com", "https://surrealdb.com/careers"),
        ("vectordotdev/vector", "Datadog", "https://www.datadoghq.com", "https://careers.datadoghq.com"),
        ("pola-rs/polars", "Polars", "https://pola.rs", "https://pola.rs/careers"),
        ("influxdata/influxdb", "InfluxData", "https://www.influxdata.com", "https://www.influxdata.com/careers/"),
        ("rerun-io/rerun", "Rerun", "https://rerun.io", "https://rerun.io/careers"),
        ("tursodatabase/turso", "Turso", "https://turso.tech", None),
        ("swc-project/swc", "Vercel", "https://vercel.com", "https://vercel.com/careers"),
        ("web-infra-dev/rspack", "ByteDance", "https://rspack.rs", "https://jobs.bytedance.com/en"),
        ("microsoft/edit", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("facebook/sapling", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("facebook/buck2", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("jj-vcs/jj", "Google", "https://jj-vcs.github.io/jj/", "https://careers.google.com"),
        ("awslabs/mountpoint-s3", "AWS", "https://aws.amazon.com", "https://www.amazon.jobs"),
        ("cloudflare/quiche", "Cloudflare", "https://www.cloudflare.com", "https://www.cloudflare.com/careers/"),
        ("huggingface/candle", "Hugging Face", "https://huggingface.co", "https://apply.workable.com/huggingface/"),
        ("huggingface/tokenizers", "Hugging Face", "https://huggingface.co", "https://apply.workable.com/huggingface/"),
        ("linkerd/linkerd2-proxy", "Buoyant", "https://buoyant.io", "https://buoyant.io/careers"),
        ("getsentry/relay", "Sentry", "https://sentry.io", "https://sentry.io/careers/"),
        ("emilk/egui", "Rerun", "https://rerun.io", "https://rerun.io/careers"),
        ("spiceai/spiceai", "Spice AI", "https://spice.ai", None),
        ("fermyon/spin", "Fermyon (Akamai)", "https://www.fermyon.com", None),
        ("tensorzero/tensorzero", "TensorZero", "https://www.tensorzero.com", None),
        ("tracel-ai/burn", "Tracel AI", "https://burn.dev", None),
        ("rustdesk/rustdesk", "RustDesk", "https://rustdesk.com", None),
        ("railwayapp/nixpacks", "Railway", "https://railway.com", "https://railway.com/careers"),
        ("windmill-labs/windmill", "Windmill Labs", "https://www.windmill.dev", None),
        ("anza-xyz/agave", "Anza", "https://www.anza.xyz", None),
        ("paritytech/polkadot-sdk", "Parity Technologies", "https://www.parity.io", "https://www.parity.io/careers"),
        ("foundry-rs/foundry", "Paradigm", "https://www.paradigm.xyz", None),
        ("paradigmxyz/reth", "Paradigm", "https://www.paradigm.xyz", None),
        ("MystenLabs/sui", "Mysten Labs", "https://www.mystenlabs.com", "https://www.mystenlabs.com/careers"),
        ("aptos-labs/aptos-core", "Aptos Labs", "https://aptoslabs.com", "https://aptoslabs.com/careers"),
    ]},
    "Java / Kotlin": {"langs": {"Java", "Kotlin"}, "top": 30, "repos": [
        ("elastic/elasticsearch", "Elastic", "https://www.elastic.co", "https://www.elastic.co/careers"),
        ("spring-projects/spring-boot", "Broadcom (VMware)", "https://spring.io", "https://www.broadcom.com/company/careers"),
        ("spring-projects/spring-framework", "Broadcom (VMware)", "https://spring.io", "https://www.broadcom.com/company/careers"),
        ("apache/kafka", "Confluent", "https://www.confluent.io", "https://careers.confluent.io"),
        ("apache/flink", "Ververica / Confluent", "https://www.ververica.com", "https://careers.confluent.io"),
        ("apache/pulsar", "StreamNative", "https://streamnative.io", "https://streamnative.io/careers"),
        ("apache/pinot", "StarTree", "https://startree.ai", "https://startree.ai/careers"),
        ("apache/druid", "Imply", "https://imply.io", "https://imply.io/careers/"),
        ("apache/doris", "VeloDB", "https://www.velodb.io", None),
        ("StarRocks/starrocks", "CelerData", "https://celerdata.com", "https://celerdata.com/careers"),
        ("trinodb/trino", "Starburst", "https://www.starburst.io", "https://www.starburst.io/careers/"),
        ("keycloak/keycloak", "Red Hat", "https://www.redhat.com", "https://www.redhat.com/en/jobs"),
        ("quarkusio/quarkus", "Red Hat", "https://www.redhat.com", "https://www.redhat.com/en/jobs"),
        ("hibernate/hibernate-orm", "Red Hat", "https://www.redhat.com", "https://www.redhat.com/en/jobs"),
        ("JetBrains/kotlin", "JetBrains", "https://www.jetbrains.com", "https://www.jetbrains.com/careers/"),
        ("JetBrains/compose-multiplatform", "JetBrains", "https://www.jetbrains.com", "https://www.jetbrains.com/careers/"),
        ("JetBrains/intellij-community", "JetBrains", "https://www.jetbrains.com", "https://www.jetbrains.com/careers/"),
        ("Kotlin/kotlinx.coroutines", "JetBrains", "https://www.jetbrains.com", "https://www.jetbrains.com/careers/"),
        ("ktorio/ktor", "JetBrains", "https://www.jetbrains.com", "https://www.jetbrains.com/careers/"),
        ("square/okhttp", "Block", "https://block.xyz", "https://block.xyz/careers"),
        ("square/retrofit", "Block", "https://block.xyz", "https://block.xyz/careers"),
        ("google/guava", "Google", "https://github.com/google/guava", "https://careers.google.com"),
        ("google/gson", "Google", "https://github.com/google/gson", "https://careers.google.com"),
        ("android/nowinandroid", "Google", "https://developer.android.com", "https://careers.google.com"),
        ("airbnb/lottie-android", "Airbnb", "https://airbnb.io/lottie/", "https://careers.airbnb.com"),
        ("conductor-oss/conductor", "Orkes", "https://orkes.io", "https://orkes.io/careers"),
        ("questdb/questdb", "QuestDB", "https://questdb.com", "https://questdb.com/careers/"),
        ("crate/crate", "CrateDB", "https://cratedb.com", "https://cratedb.com/careers"),
        ("neo4j/neo4j", "Neo4j", "https://neo4j.com", "https://neo4j.com/careers/"),
        ("opensearch-project/OpenSearch", "AWS", "https://opensearch.org", "https://www.amazon.jobs"),
        ("vespa-engine/vespa", "Vespa.ai", "https://vespa.ai", "https://vespa.ai/careers"),
        ("camunda/camunda", "Camunda", "https://camunda.com", "https://camunda.com/careers/"),
        ("thingsboard/thingsboard", "ThingsBoard", "https://thingsboard.io", "https://thingsboard.io/careers/"),
        ("jenkinsci/jenkins", "CloudBees", "https://www.cloudbees.com", "https://www.cloudbees.com/careers"),
        ("gradle/gradle", "Gradle Inc.", "https://gradle.com", "https://gradle.com/careers/"),
        ("apache/dubbo", "Alibaba", "https://dubbo.apache.org", "https://talent.alibaba.com"),
        ("alibaba/nacos", "Alibaba", "https://nacos.io", "https://talent.alibaba.com"),
        ("alibaba/arthas", "Alibaba", "https://arthas.aliyun.com", "https://talent.alibaba.com"),
        ("signalapp/Signal-Android", "Signal", "https://signal.org", "https://signal.org/workworkwork/"),
        ("duckduckgo/Android", "DuckDuckGo", "https://duckduckgo.com", "https://duckduckgo.com/hiring"),
        ("openrewrite/rewrite", "Moderne", "https://www.moderne.ai", "https://www.moderne.ai/careers"),
        ("testcontainers/testcontainers-java", "Docker (AtomicJar)", "https://www.docker.com", "https://www.docker.com/careers/"),
        ("SonarSource/sonarqube", "SonarSource", "https://www.sonarsource.com", "https://www.sonarsource.com/company/careers/"),
        ("dbeaver/dbeaver", "DBeaver Corp", "https://dbeaver.com", None),
        ("vaadin/flow", "Vaadin", "https://vaadin.com", "https://vaadin.com/careers"),
    ]},
    "C / C++": {"langs": {"C", "C++"}, "top": 30, "repos": [
        ("ClickHouse/ClickHouse", "ClickHouse", "https://clickhouse.com", "https://clickhouse.com/company/careers"),
        ("duckdb/duckdb", "DuckDB Labs", "https://duckdblabs.com", None),
        ("redis/redis", "Redis", "https://redis.io", "https://redis.io/careers/"),
        ("dragonflydb/dragonfly", "DragonflyDB", "https://www.dragonflydb.io", "https://www.dragonflydb.io/careers"),
        ("scylladb/scylladb", "ScyllaDB", "https://www.scylladb.com", "https://www.scylladb.com/company/careers/"),
        ("netdata/netdata", "Netdata", "https://www.netdata.cloud", "https://www.netdata.cloud/careers/"),
        ("falcosecurity/falco", "Sysdig", "https://sysdig.com", "https://sysdig.com/careers/"),
        ("ggml-org/llama.cpp", "ggml.ai", "https://ggml.ai", None),
        ("microsoft/terminal", "Microsoft", "https://www.microsoft.com", "https://careers.microsoft.com"),
        ("microsoft/onnxruntime", "Microsoft", "https://onnxruntime.ai", "https://careers.microsoft.com"),
        ("citusdata/citus", "Microsoft", "https://www.citusdata.com", "https://careers.microsoft.com"),
        ("protocolbuffers/protobuf", "Google", "https://protobuf.dev", "https://careers.google.com"),
        ("google/googletest", "Google", "https://google.github.io/googletest/", "https://careers.google.com"),
        ("tensorflow/tensorflow", "Google", "https://www.tensorflow.org", "https://careers.google.com"),
        ("facebook/folly", "Meta", "https://about.meta.com", "https://www.metacareers.com"),
        ("facebook/rocksdb", "Meta", "https://rocksdb.org", "https://www.metacareers.com"),
        ("NVIDIA/cutlass", "NVIDIA", "https://www.nvidia.com", "https://www.nvidia.com/en-us/about-nvidia/careers/"),
        ("openvinotoolkit/openvino", "Intel", "https://www.intel.com", "https://jobs.intel.com"),
        ("apple/foundationdb", "Apple", "https://www.foundationdb.org", "https://jobs.apple.com"),
        ("mongodb/mongo", "MongoDB", "https://www.mongodb.com", "https://www.mongodb.com/company/careers"),
        ("timescale/timescaledb", "Tiger Data", "https://www.tigerdata.com", "https://www.tigerdata.com/careers"),
        ("memgraph/memgraph", "Memgraph", "https://memgraph.com", "https://memgraph.com/careers"),
        ("arangodb/arangodb", "ArangoDB", "https://arangodb.com", "https://arangodb.com/careers/"),
        ("yugabyte/yugabyte-db", "Yugabyte", "https://www.yugabyte.com", "https://www.yugabyte.com/careers/"),
        ("oceanbase/oceanbase", "OceanBase (Ant Group)", "https://www.oceanbase.com", None),
        ("taosdata/TDengine", "TDengine", "https://tdengine.com", "https://tdengine.com/careers/"),
        ("typesense/typesense", "Typesense", "https://typesense.org", None),
        ("manticoresoftware/manticoresearch", "Manticore Software", "https://manticoresearch.com", "https://manticoresearch.com/careers/"),
        ("fluent/fluent-bit", "Chronosphere", "https://chronosphere.io", "https://chronosphere.io/careers/"),
        ("nginx/nginx", "F5", "https://nginx.org", "https://www.f5.com/company/careers"),
        ("wolfSSL/wolfssl", "wolfSSL", "https://www.wolfssl.com", "https://www.wolfssl.com/careers/"),
        ("espressif/esp-idf", "Espressif", "https://www.espressif.com", "https://www.espressif.com/en/company/careers"),
        ("LadybirdBrowser/ladybird", "Ladybird Browser Initiative", "https://ladybird.org", None),
        ("prusa3d/PrusaSlicer", "Prusa Research", "https://www.prusa3d.com", "https://www.prusa3d.com/page/jobs_485/"),
        ("Tencent/ncnn", "Tencent", "https://www.tencent.com", "https://careers.tencent.com"),
        ("alibaba/MNN", "Alibaba", "https://www.alibabagroup.com", "https://talent.alibaba.com"),
        ("wazuh/wazuh", "Wazuh", "https://wazuh.com", "https://wazuh.com/careers/"),
    ]},
}

SOCIAL = {"reddit.com": "reddit", "youtube.com": "youtube", "youtu.be": "youtube", "linkedin.com": "linkedin",
          "bsky.app": "bluesky", "mastodon.social": "mastodon", "fosstodon.org": "mastodon"}
KEEP = {"slack", "discord", "zulip", "matrix", "gitter", "telegram", "whatsapp", "mattermost", "rocketchat", "irc", "forum", "x"}
SINCE = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
_reach = {}


def reachable(url):
    """Careers URL loads (2xx/3xx, or bot-blocked 401/403/429 which means the page exists)."""
    if url in _reach:
        return _reach[url]
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            ok = r.status < 400
    except urllib.error.HTTPError as e:
        ok = e.code in (401, 403, 429)
    except Exception:  # noqa: BLE001 - dns/timeouts = not reachable
        ok = False
    _reach[url] = ok
    return ok


def channels(readme, homepage):
    found = {}
    for url in re.findall(r"https?://[^\s)\"'<>\]]+", readme):
        url = url.rstrip(".,;")
        h = host(url)
        if "shields.io" in h or "badge" in url or re.search(r"\.(svg|png|gif|jpe?g)(\?|$)", url) or "githubusercontent" in h:
            continue
        kind = next((v for k, v in SOCIAL.items() if h == k or h.endswith("." + k)), None)
        if not kind:
            kind = classify("chat", url)[0]
            if kind == "chat":  # unknown host: only community/forum-looking pages count
                kind = "forum" if re.search(r"community|discuss|forum", h) else None
            elif kind not in KEEP:
                kind = None
        if kind and url not in found:
            found[url] = kind
    out, seen = [], {}
    for url, kind in found.items():  # 2 chat links / 1 social link per kind keeps busy READMEs sane
        if seen.get(kind, 0) < (2 if kind in KEEP - {"x"} else 1):
            seen[kind] = seen.get(kind, 0) + 1
            out.append({"type": kind, "url": url})
    return out


def search_count(q, per_page=1):
    s, r = get(f"{GH}/search/issues?per_page={per_page}&sort=updated&q={urllib.parse.quote(q)}", search=True)
    return (r or {}) if s == 200 else {}


def project(c):
    full, backer, site, careers = c
    s, r = get(f"{GH}/repos/{full}")
    if s != 200:
        log(f"  skip {full}: {s}")
        return None
    full = r["full_name"]
    s, owner = get(f"{GH}/users/{r['owner']['login']}")
    s, langs = get(f"{GH}/repos/{full}/languages")
    tot = sum((langs or {}).values()) or 1
    s, rd = get(f"{GH}/repos/{full}/readme")
    readme = base64.b64decode(rd["content"]).decode("utf-8", "replace") if s == 200 and rd.get("content") else ""
    s, cp = get(f"{GH}/repos/{full}/community/profile")
    files = (cp or {}).get("files") or {}
    gfi_q = f'repo:{full} is:issue is:open label:"good first issue","good-first-issue","E-easy","beginner","help wanted"'
    merged_q = f"repo:{full} is:pr is:merged merged:>={SINCE}"
    open_q = f"repo:{full} is:pr is:open"
    merged = search_count(merged_q, per_page=5)
    o = owner or {}
    return {
        "repo": full, "name": r["name"], "desc": r.get("description"), "url": r["html_url"], "homepage": r.get("homepage"),
        "lang": r.get("language"), "langs": {k: round(v * 100 / tot, 1) for k, v in sorted((langs or {}).items(), key=lambda kv: -kv[1])[:6]},
        "stars": r["stargazers_count"], "forks": r["forks_count"], "issues": r["open_issues_count"], "topics": r.get("topics") or [],
        "license": (r.get("license") or {}).get("spdx_id"), "created": r.get("created_at"), "pushed": r.get("pushed_at"),
        "owner": {"login": o.get("login"), "name": o.get("name"), "type": o.get("type"), "avatar": o.get("avatar_url"),
                  "blog": o.get("blog"), "twitter": o.get("twitter_username"), "location": o.get("location"),
                  "followers": o.get("followers"), "repos": o.get("public_repos")},
        "backer": backer, "backer_site": site, "careers": careers if careers and reachable(careers) else None,
        "careers_tried": careers,
        "contributing": ((files.get("contributing") or {}).get("html_url")), "coc": ((files.get("code_of_conduct") or {}).get("html_url")),
        "channels": channels(readme, r.get("homepage")),
        "prs": {"open": search_count(open_q).get("total_count"), "merged30": merged.get("total_count"),
                "gfi": search_count(gfi_q).get("total_count"),
                "recent": [{"t": it["title"], "u": it["html_url"], "by": (it.get("user") or {}).get("login")} for it in merged.get("items") or []],
                "open_url": f"https://github.com/{full}/pulls",
                "merged_url": "https://github.com/search?type=pullrequests&q=" + urllib.parse.quote(merged_q),
                "gfi_url": "https://github.com/search?type=issues&q=" + urllib.parse.quote(gfi_q)},
    }


def main():
    groups = []
    for title, g in CANDIDATES.items():
        # cheap pass first: language + stars, so search budget goes only to projects that make the cut
        metas = pmap(lambda c: (c, get(f"{GH}/repos/{c[0]}")), g["repos"])
        ok = [c for c, (s, r) in metas if s == 200 and r.get("language") in g["langs"]]
        dropped = [f"{c[0]} ({(r or {}).get('language')})" for c, (s, r) in metas if c not in ok]
        ok.sort(key=lambda c: -dict(metas)[c][1]["stargazers_count"])
        picked = [p for p in pmap(project, ok[:g["top"]], workers=4) if p]
        log(f"{title}: {len(picked)}/{g['top']} (dropped: {', '.join(dropped) or 'none'})")
        groups.append({"title": title, "projects": picked})
    data = {"generated": datetime.date.today().isoformat(), "since": SINCE, "groups": groups}
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    OUT.mkdir(exist_ok=True)
    (OUT / "oss.json").write_text(txt, "utf-8")
    (OUT / "oss.js").write_text("window.OSS=" + txt + ";\n", "utf-8")
    log(f"wrote data/oss.json: {sum(len(g['projects']) for g in groups)} projects, {len(txt) // 1024} KB")


if __name__ == "__main__":
    main()
