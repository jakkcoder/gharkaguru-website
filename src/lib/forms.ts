import { useForm, type FieldValues, type UseFormProps, type UseFormReturn } from 'react-hook-form'

export function useAppForm<TFieldValues extends FieldValues = FieldValues, TContext = unknown>(
  props: UseFormProps<TFieldValues, TContext> = {} as UseFormProps<TFieldValues, TContext>,
): UseFormReturn<TFieldValues, TContext> {
  return useForm<TFieldValues, TContext>({
    mode: 'onChange',
    reValidateMode: 'onChange',
    ...props,
  })
}
