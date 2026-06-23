'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardList, Copy, ListPlus, Pencil, SlidersHorizontal, Trash2, X } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  createCustomField,
  createItemTemplate,
  createItemType,
  deleteCustomField,
  deleteItemTemplate,
  deleteItemType,
  listCustomFields,
  listItemTemplates,
  listItemTypes,
  updateItemTemplate,
  type CustomFieldCreate,
  type ItemTemplatePayload,
  type ItemTemplateRead,
} from '@/lib/api/customization'
import { useAccessToken } from '@/lib/auth/use-auth'

type FieldType = CustomFieldCreate['field_type']

const FIELD_TYPES: FieldType[] = ['text', 'number', 'date', 'bool']

function fieldTypeLabel(t: ReturnType<typeof useTranslations>, type: string) {
  if (type === 'text' || type === 'number' || type === 'date' || type === 'bool') {
    return t(`settings.customization.fieldTypes.${type}`)
  }
  return type
}

function templateSummary(t: ReturnType<typeof useTranslations>, payload: ItemTemplatePayload) {
  const itemName = typeof payload.name === 'string' && payload.name.trim() ? payload.name : null
  const quantity =
    typeof payload.quantity === 'number' || typeof payload.quantity === 'string'
      ? String(payload.quantity)
      : null

  if (itemName && quantity !== null) {
    return t('settings.customization.templateSummaryNameQty', { name: itemName, quantity })
  }
  if (itemName) return itemName

  const keys = Object.keys(payload)
  if (keys.length === 0) return t('settings.customization.emptyPayload')
  return keys.slice(0, 3).join(', ')
}

function cloneTemplatePayload(payload: ItemTemplatePayload) {
  return JSON.parse(JSON.stringify(payload)) as ItemTemplatePayload
}

export function CustomizationPanel() {
  const t = useTranslations()
  const token = useAccessToken()
  const queryClient = useQueryClient()

  const [typeName, setTypeName] = useState('')
  const [typeIcon, setTypeIcon] = useState('')
  const [fieldName, setFieldName] = useState('')
  const [fieldType, setFieldType] = useState<FieldType>('text')
  const [templateName, setTemplateName] = useState('')
  const [templateItemName, setTemplateItemName] = useState('')
  const [templateQuantity, setTemplateQuantity] = useState('')
  const [templateNotes, setTemplateNotes] = useState('')
  const [templateCustomValues, setTemplateCustomValues] = useState<Record<string, string | boolean>>({})
  const [editingTemplateId, setEditingTemplateId] = useState<number | null>(null)

  const itemTypes = useQuery({
    queryKey: ['customization', 'item-types'],
    queryFn: () => listItemTypes(token),
    enabled: token !== null,
  })
  const customFields = useQuery({
    queryKey: ['customization', 'custom-fields'],
    queryFn: () => listCustomFields(token),
    enabled: token !== null,
  })
  const templates = useQuery({
    queryKey: ['customization', 'item-templates'],
    queryFn: () => listItemTemplates(token),
    enabled: token !== null,
  })

  const invalidateCustomization = () => {
    queryClient.invalidateQueries({ queryKey: ['customization'] })
  }

  const createType = useMutation({
    mutationFn: () =>
      createItemType(
        {
          name: typeName.trim(),
          icon: typeIcon.trim() ? typeIcon.trim() : null,
        },
        token,
      ),
    onSuccess: () => {
      setTypeName('')
      setTypeIcon('')
      invalidateCustomization()
      toast.success(t('settings.customization.toast.saved'))
    },
    onError: () => toast.error(t('settings.customization.toast.saveFailed')),
  })

  const createField = useMutation({
    mutationFn: () =>
      createCustomField(
        {
          name: fieldName.trim(),
          field_type: fieldType,
        },
        token,
      ),
    onSuccess: () => {
      setFieldName('')
      setFieldType('text')
      invalidateCustomization()
      toast.success(t('settings.customization.toast.saved'))
    },
    onError: () => toast.error(t('settings.customization.toast.saveFailed')),
  })

  const buildTemplatePayload = () => {
    const payload: ItemTemplatePayload = {}
    if (templateItemName.trim()) payload.name = templateItemName.trim()
    if (templateQuantity.trim()) payload.quantity = Number(templateQuantity)
    if (templateNotes.trim()) payload.notes = templateNotes.trim()
    const customValues: Record<string, unknown> = {}
    for (const field of customFields.data ?? []) {
      const key = String(field.id)
      const raw = templateCustomValues[key]
      if (raw === undefined) continue

      if (field.field_type === 'bool') {
        if (raw === true) customValues[key] = true
        continue
      }

      if (typeof raw !== 'string' || raw.trim() === '') continue

      if (field.field_type === 'number') {
        const numberValue = Number(raw)
        if (!Number.isNaN(numberValue)) customValues[key] = numberValue
        continue
      }

      customValues[key] = raw.trim()
    }
    if (Object.keys(customValues).length > 0) {
      payload.custom_values = customValues
    }
    return payload
  }

  const resetTemplateForm = () => {
    setTemplateName('')
    setTemplateItemName('')
    setTemplateQuantity('')
    setTemplateNotes('')
    setTemplateCustomValues({})
    setEditingTemplateId(null)
  }

  const createTemplate = useMutation({
    mutationFn: () => {
      return createItemTemplate({ name: templateName.trim(), payload: buildTemplatePayload() }, token)
    },
    onSuccess: () => {
      resetTemplateForm()
      invalidateCustomization()
      toast.success(t('settings.customization.toast.saved'))
    },
    onError: () => toast.error(t('settings.customization.toast.saveFailed')),
  })
  const updateTemplate = useMutation({
    mutationFn: (id: number) =>
      updateItemTemplate(
        id,
        { name: templateName.trim(), payload: buildTemplatePayload() },
        token,
      ),
    onSuccess: () => {
      resetTemplateForm()
      invalidateCustomization()
      toast.success(t('settings.customization.toast.saved'))
    },
    onError: () => toast.error(t('settings.customization.toast.saveFailed')),
  })

  const removeType = useMutation({
    mutationFn: (id: number) => deleteItemType(id, token),
    onSuccess: invalidateCustomization,
    onError: () => toast.error(t('settings.customization.toast.deleteFailed')),
  })
  const removeField = useMutation({
    mutationFn: (id: number) => deleteCustomField(id, token),
    onSuccess: invalidateCustomization,
    onError: () => toast.error(t('settings.customization.toast.deleteFailed')),
  })
  const removeTemplate = useMutation({
    mutationFn: (id: number) => deleteItemTemplate(id, token),
    onSuccess: invalidateCustomization,
    onError: () => toast.error(t('settings.customization.toast.deleteFailed')),
  })
  const duplicateTemplate = useMutation({
    mutationFn: (template: ItemTemplateRead) =>
      createItemTemplate(
        {
          name: t('settings.customization.templateCopyName', { name: template.name }),
          payload: cloneTemplatePayload(template.payload),
        },
        token,
      ),
    onSuccess: () => {
      invalidateCustomization()
      toast.success(t('settings.customization.toast.saved'))
    },
    onError: () => toast.error(t('settings.customization.toast.saveFailed')),
  })

  const isLoading = itemTypes.isLoading || customFields.isLoading || templates.isLoading

  const updateTemplateCustomValue = (key: string, value: string) => {
    setTemplateCustomValues((current) => ({
      ...current,
      [key]: value,
    }))
  }

  const startEditingTemplate = (template: ItemTemplateRead) => {
    const payload = template.payload
    const customValues =
      payload.custom_values && typeof payload.custom_values === 'object'
        ? (payload.custom_values as Record<string, unknown>)
        : {}
    const nextCustomValues: Record<string, string | boolean> = {}

    for (const [key, value] of Object.entries(customValues)) {
      if (typeof value === 'boolean') {
        if (value) nextCustomValues[key] = true
        continue
      }
      if (value !== null && value !== undefined) {
        nextCustomValues[key] = String(value)
      }
    }

    setEditingTemplateId(template.id)
    setTemplateName(template.name)
    setTemplateItemName(typeof payload.name === 'string' ? payload.name : '')
    setTemplateQuantity(
      typeof payload.quantity === 'number' || typeof payload.quantity === 'string'
        ? String(payload.quantity)
        : '',
    )
    setTemplateNotes(typeof payload.notes === 'string' ? payload.notes : '')
    setTemplateCustomValues(nextCustomValues)
  }

  if (isLoading) {
    return <p className="text-muted-foreground text-sm">{t('settings.customization.loading')}</p>
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold">{t('settings.customization.title')}</h2>
        <p className="text-muted-foreground mt-1 max-w-3xl text-sm">
          {t('settings.customization.description')}
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <section className="bg-card rounded-lg border p-4">
          <div className="flex items-start gap-3">
            <div className="bg-primary/10 text-primary grid h-10 w-10 shrink-0 place-items-center rounded-md">
              <SlidersHorizontal className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-base font-semibold">{t('settings.customization.typesTitle')}</h3>
              <p className="text-muted-foreground mt-1 text-sm">
                {t('settings.customization.typesDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3">
            <div className="grid gap-2">
              <Label htmlFor="item-type-name">{t('settings.customization.typeNameLabel')}</Label>
              <Input
                id="item-type-name"
                value={typeName}
                onChange={(event) => setTypeName(event.target.value)}
                placeholder={t('settings.customization.typeNamePlaceholder')}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="item-type-icon">{t('settings.customization.typeIconLabel')}</Label>
              <Input
                id="item-type-icon"
                value={typeIcon}
                onChange={(event) => setTypeIcon(event.target.value)}
                placeholder={t('settings.customization.typeIconPlaceholder')}
              />
            </div>
            <Button
              type="button"
              onClick={() => createType.mutate()}
              disabled={!typeName.trim() || createType.isPending}
            >
              <ListPlus className="mr-2 h-4 w-4" aria-hidden="true" />
              {createType.isPending
                ? t('settings.customization.creating')
                : t('settings.customization.createType')}
            </Button>
          </div>

          <ul className="mt-5 divide-y rounded-md border">
            {(itemTypes.data ?? []).length === 0 ? (
              <li className="text-muted-foreground p-3 text-sm">
                {t('settings.customization.emptyTypes')}
              </li>
            ) : (
              itemTypes.data?.map((type) => (
                <li key={type.id} className="flex items-center justify-between gap-3 p-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{type.name}</p>
                    {type.icon ? (
                      <p className="text-muted-foreground truncate text-xs">{type.icon}</p>
                    ) : null}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeType.mutate(type.id)}
                    aria-label={t('settings.customization.deleteType', { name: type.name })}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </li>
              ))
            )}
          </ul>
        </section>

        <section className="bg-card rounded-lg border p-4">
          <div className="flex items-start gap-3">
            <div className="bg-primary/10 text-primary grid h-10 w-10 shrink-0 place-items-center rounded-md">
              <ClipboardList className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-base font-semibold">{t('settings.customization.fieldsTitle')}</h3>
              <p className="text-muted-foreground mt-1 text-sm">
                {t('settings.customization.fieldsDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3">
            <div className="grid gap-2">
              <Label htmlFor="custom-field-name">{t('settings.customization.fieldNameLabel')}</Label>
              <Input
                id="custom-field-name"
                value={fieldName}
                onChange={(event) => setFieldName(event.target.value)}
                placeholder={t('settings.customization.fieldNamePlaceholder')}
              />
            </div>
            <div className="grid gap-2">
              <Label id="custom-field-type-label">{t('settings.customization.fieldTypeLabel')}</Label>
              <Select value={fieldType} onValueChange={(value) => setFieldType(value as FieldType)}>
                <SelectTrigger aria-labelledby="custom-field-type-label">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FIELD_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {fieldTypeLabel(t, type)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              type="button"
              onClick={() => createField.mutate()}
              disabled={!fieldName.trim() || createField.isPending}
            >
              <ListPlus className="mr-2 h-4 w-4" aria-hidden="true" />
              {createField.isPending
                ? t('settings.customization.creating')
                : t('settings.customization.createField')}
            </Button>
          </div>

          <ul className="mt-5 divide-y rounded-md border">
            {(customFields.data ?? []).length === 0 ? (
              <li className="text-muted-foreground p-3 text-sm">
                {t('settings.customization.emptyFields')}
              </li>
            ) : (
              customFields.data?.map((field) => (
                <li key={field.id} className="flex items-center justify-between gap-3 p-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{field.name}</p>
                    <Badge variant="secondary" className="mt-1">
                      {fieldTypeLabel(t, field.field_type)}
                    </Badge>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeField.mutate(field.id)}
                    aria-label={t('settings.customization.deleteField', { name: field.name })}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </li>
              ))
            )}
          </ul>
        </section>

        <section className="bg-card rounded-lg border p-4">
          <div className="flex items-start gap-3">
            <div className="bg-primary/10 text-primary grid h-10 w-10 shrink-0 place-items-center rounded-md">
              <ClipboardList className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-base font-semibold">{t('settings.customization.templatesTitle')}</h3>
              <p className="text-muted-foreground mt-1 text-sm">
                {t('settings.customization.templatesDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3">
            <div className="grid gap-2">
              <Label htmlFor="template-name">{t('settings.customization.templateNameLabel')}</Label>
              <Input
                id="template-name"
                value={templateName}
                onChange={(event) => setTemplateName(event.target.value)}
                placeholder={t('settings.customization.templateNamePlaceholder')}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="template-item-name">
                {t('settings.customization.templateItemNameLabel')}
              </Label>
              <Input
                id="template-item-name"
                value={templateItemName}
                onChange={(event) => setTemplateItemName(event.target.value)}
                placeholder={t('settings.customization.templateItemNamePlaceholder')}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="template-quantity">
                {t('settings.customization.templateQuantityLabel')}
              </Label>
              <Input
                id="template-quantity"
                type="number"
                min={0}
                value={templateQuantity}
                onChange={(event) => setTemplateQuantity(event.target.value)}
                placeholder="1"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="template-notes">{t('settings.customization.templateNotesLabel')}</Label>
              <Textarea
                id="template-notes"
                rows={2}
                value={templateNotes}
                onChange={(event) => setTemplateNotes(event.target.value)}
              />
            </div>
            {(customFields.data ?? []).length > 0 ? (
              <div className="grid gap-3 rounded-md border bg-muted/30 p-3">
                <p className="text-sm font-medium">
                  {t('settings.customization.templateCustomValuesTitle')}
                </p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {customFields.data?.map((field) => {
                    const key = String(field.id)
                    const fieldId = `template-custom-field-${field.id}`

                    if (field.field_type === 'bool') {
                      return (
                        <div key={field.id} className="flex items-center gap-2 rounded-md border bg-background px-3 py-2">
                          <Checkbox
                            id={fieldId}
                            checked={templateCustomValues[key] === true}
                            onCheckedChange={(checked) => {
                              setTemplateCustomValues((current) => {
                                const next = { ...current }
                                if (checked === true) next[key] = true
                                else delete next[key]
                                return next
                              })
                            }}
                          />
                          <Label htmlFor={fieldId}>{field.name}</Label>
                        </div>
                      )
                    }

                    const inputType =
                      field.field_type === 'number'
                        ? 'number'
                        : field.field_type === 'date'
                          ? 'date'
                          : 'text'

                    return (
                      <div key={field.id} className="grid gap-2">
                        <Label htmlFor={fieldId}>{field.name}</Label>
                        <Input
                          id={fieldId}
                          type={inputType}
                          value={String(templateCustomValues[key] ?? '')}
                          onInput={(event) => {
                            updateTemplateCustomValue(key, event.currentTarget.value)
                          }}
                          onChange={(event) => {
                            updateTemplateCustomValue(key, event.target.value)
                          }}
                        />
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : null}
            <Button
              type="button"
              onClick={() =>
                editingTemplateId === null
                  ? createTemplate.mutate()
                  : updateTemplate.mutate(editingTemplateId)
              }
              disabled={!templateName.trim() || createTemplate.isPending || updateTemplate.isPending}
            >
              <ListPlus className="mr-2 h-4 w-4" aria-hidden="true" />
              {editingTemplateId === null
                ? createTemplate.isPending
                  ? t('settings.customization.creating')
                  : t('settings.customization.createTemplate')
                : updateTemplate.isPending
                  ? t('settings.customization.updating')
                  : t('settings.customization.updateTemplate')}
            </Button>
            {editingTemplateId !== null ? (
              <Button type="button" variant="outline" onClick={resetTemplateForm}>
                <X className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('settings.customization.cancelTemplateEdit')}
              </Button>
            ) : null}
          </div>

          <ul className="mt-5 divide-y rounded-md border">
            {(templates.data ?? []).length === 0 ? (
              <li className="text-muted-foreground p-3 text-sm">
                {t('settings.customization.emptyTemplates')}
              </li>
            ) : (
              templates.data?.map((template) => (
                <li
                  key={template.id}
                  className="flex items-center justify-between gap-3 p-3 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{template.name}</p>
                    <p className="text-muted-foreground truncate text-xs">
                      {templateSummary(t, template.payload)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => startEditingTemplate(template)}
                      aria-label={t('settings.customization.editTemplate', {
                        name: template.name,
                      })}
                    >
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => duplicateTemplate.mutate(template)}
                      disabled={duplicateTemplate.isPending}
                      aria-label={t('settings.customization.duplicateTemplate', {
                        name: template.name,
                      })}
                    >
                      <Copy className="h-4 w-4" aria-hidden="true" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeTemplate.mutate(template.id)}
                      aria-label={t('settings.customization.deleteTemplate', {
                        name: template.name,
                      })}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                </li>
              ))
            )}
          </ul>
        </section>
      </div>
    </div>
  )
}
