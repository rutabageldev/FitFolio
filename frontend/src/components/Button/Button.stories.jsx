import { Button } from './Button.jsx';

export default {
  title: 'Primitives/Button',
  component: Button,
  args: {
    children: 'Button',
  },
};

export const Primary = {
  args: { variant: 'primary' },
};

export const Secondary = {
  args: { variant: 'secondary' },
};
