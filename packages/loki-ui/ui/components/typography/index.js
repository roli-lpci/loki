import React from 'react';
export function Typography({ as = 'span', children, ...props }) { return React.createElement(as, props, children); }
