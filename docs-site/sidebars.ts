import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'index',
    'editions',
    {
      type: 'category',
      label: 'Core Concepts & Architecture',
      items: [
        'architecture',
        'workflow_diagram',
        'data_pipeline_diagram',
      ],
    },
    {
      type: 'category',
      label: 'User Guides & Operations',
      items: [
        'getting_data_in',
        'workspace_management',
      ],
    },
    {
      type: 'category',
      label: 'For Contributors & Developers',
      items: [
        'development',
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
        'auth-strategy',
        'changelog',
        'admin-policy',
        'privacy-policy',
        'terms-of-service'
      ],
    },
  ],
};

export default sidebars;
