import React from 'react';
export function Select({ value, onValueChange, children, ...props }) { return React.createElement('select', { ...props, value, onChange: (event) => onValueChange?.(event.target.value) }, children); }
export function SelectOption({ value, children, ...props }) { return React.createElement('option', { ...props, value }, children); }
