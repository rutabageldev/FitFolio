import PropTypes from 'prop-types';
import './Button.css';

export function Button({ variant = 'primary', children, ...props }) {
  return (
    <button className={`ff-btn ${variant}`} type="button" {...props}>
      {children}
    </button>
  );
}

Button.propTypes = {
  variant: PropTypes.string,
  children: PropTypes.node.isRequired,
};
