// shadcn/ui Button pattern, MIT. Local copy; no remote runtime dependencies.
import * as React from 'react'
import {Slot} from '@radix-ui/react-slot'
import {cva,type VariantProps} from 'class-variance-authority'
import {cn} from '@/lib/utils'

const buttonVariants=cva('button',{variants:{variant:{default:'button-primary',secondary:'button-secondary',ghost:'button-ghost',outline:'button-outline',destructive:'button-destructive'},size:{default:'',sm:'button-sm',icon:'button-icon'}},defaultVariants:{variant:'default',size:'default'}})
type Props=React.ButtonHTMLAttributes<HTMLButtonElement>&VariantProps<typeof buttonVariants>&{asChild?:boolean}
export const Button=React.forwardRef<HTMLButtonElement,Props>(({className,variant,size,asChild=false,...props},ref)=>{
  const Component=asChild?Slot:'button'
  return <Component className={cn(buttonVariants({variant,size,className}))} ref={ref} {...props}/>
})
Button.displayName='Button'
