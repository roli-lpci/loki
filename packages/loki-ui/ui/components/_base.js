import React from 'react';
export function component(tag = 'div') {
  return React.forwardRef(function LokiUiComponent(props, ref) {
    const { children, prefix, suffix, asChild, variant, size, loading, open, ...rest } = props ?? {};
    if (open === false) return null;
    return React.createElement(tag, { ...rest, ref }, prefix, children, suffix);
  });
}
