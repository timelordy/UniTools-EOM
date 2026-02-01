import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary'
  size?: 'normal' | 'large'
}

export const Button: React.FC<ButtonProps> = ({ 
  children, 
  variant = 'primary', 
  size = 'normal',
  className = '',
  ...props 
}) => {
  const baseClass = variant === 'primary' ? 'btn btn-primary' : 'btn btn-secondary'
  const sizeClass = size === 'large' ? 'btn-large' : ''
  
  return (
    <button 
      className={`${baseClass} ${sizeClass} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
