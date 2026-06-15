import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: '📖 The Journey',
      collapsed: false,
      items: [
        'journey/from-chat-to-agent',
        'journey/ground-it-in-data',
        'journey/give-it-context',
        'journey/arm-it-with-tools',
        'journey/build-reusable-skills',
        'journey/ship-it',
      ],
    },
    {
      type: 'category',
      label: '🧩 Building Blocks',
      items: [
        'building-blocks/choose-data-platform',
        'building-blocks/fabric-data-agent',
        'building-blocks/databricks-genie',
        'building-blocks/workiq',
        'building-blocks/mcp',
        'building-blocks/foundry',
        'building-blocks/skills',
        'building-blocks/report-generation',
        'building-blocks/quota-pipeline',
        'building-blocks/wwi-dataset',
      ],
    },
    {
      type: 'category',
      label: '🏗️ Architecture',
      items: [
        'architecture/system-overview',
        'architecture/cli-surface',
        'architecture/foundry-surface',
        'architecture/auth-patterns',
      ],
    },
    {
      type: 'category',
      label: '🛠️ Workshop Guide',
      items: [
        'workshop/facilitator-guide',
        'workshop/setup',
        'workshop/demo-script',
        'workshop/costs',
      ],
   },
 ],
};

export default sidebars;
