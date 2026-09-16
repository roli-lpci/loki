import React from 'react';

const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);

export function component(tag = 'div') {
  return React.forwardRef(function LokiUiComponent(props, ref) {
    const {
      children,
      prefix,
      suffix,
      asChild,
      variant,
      size,
      loading,
      open,
      ghost,
      outlined,
      ...rest
    } = props ?? {};

    if (open === false) return null;

    const elementProps = { ...rest, ref };

    if (VOID_TAGS.has(tag)) {
      return React.createElement(tag, elementProps);
    }

    return React.createElement(tag, elementProps, prefix, children, suffix);
  });
}
