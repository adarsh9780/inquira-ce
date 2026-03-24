import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    {
      type: 'category',
      label: 'Welcome / Getting Started',
      items: [
        'index',
        'install',
        'downloads',
        'overview'
      ],
    },
    {
      type: 'category',
      label: 'Editions (Free, Pro & Enterprise)',
      items: [
        'editions',
        'auth-strategy'
      ],
    },
    {
      type: 'category',
      label: 'For Contributors & Developers',
      items: [
        'development',
        'architecture',
        'workflow_diagram',
        'data_pipeline_diagram',
        'contributing',
        'commit-and-release',
        'ci-and-release-automation',
        'release_process'
      ],
    },
    {
      type: 'category',
      label: 'Future Features & Roadmap',
      items: [
        'roadmap',
        'plans_for_future'
      ],
    },
    {
      type: 'category',
      label: 'Legal & Admin',
      items: [
        'changelog',
        'admin-policy',
        'privacy-policy',
        'terms-of-service'
      ],
    },
  ],
};

export default sidebars;
