import React from 'react';
export const Switch = React.forwardRef(function Switch({ checked, onCheckedChange, ...props }, ref) { return React.createElement('input', { ...props, ref, type: 'checkbox', checked: Boolean(checked), onChange: (event) => onCheckedChange?.(event.target.checked) }); });
