import '../src/index.css';
import '../src/styles/tokens.css';
import '../src/styles/fonts.css';

/** @type { import('@storybook/react').Preview } */
const preview = {
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    options: {
      storySort: {
        order: ['Primitives', 'Components', 'Patterns'],
      },
    },
  },
};

export default preview;
