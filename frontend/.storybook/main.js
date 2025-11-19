/** @type { import('@storybook/react-webpack5').StorybookConfig } */
const config = {
  framework: '@storybook/react-webpack5',
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: ['@storybook/addon-essentials', '@storybook/addon-interactions', '@storybook/addon-a11y'],
  staticDirs: ['../public'],
  docs: {
    autodocs: true,
  },
  webpackFinal: async (config) => {
    // Ensure JSX is transpiled for React 18/19 projects without a Babel config
    config.module.rules.push({
      test: /\.(js|jsx)$/,
      exclude: /node_modules/,
      use: {
        loader: 'babel-loader',
        options: {
          presets: ['@babel/preset-env', ['@babel/preset-react', { runtime: 'automatic' }]],
        },
      },
    });
    config.resolve.extensions.push('.js', '.jsx');
    return config;
  },
};

export default config;
