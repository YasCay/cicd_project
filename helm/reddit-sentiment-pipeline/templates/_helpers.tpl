{{/*
Expand the name of the chart.
*/}}
{{- define "reddit-sentiment-pipeline.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "reddit-sentiment-pipeline.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "reddit-sentiment-pipeline.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "reddit-sentiment-pipeline.labels" -}}
helm.sh/chart: {{ include "reddit-sentiment-pipeline.chart" . }}
{{ include "reddit-sentiment-pipeline.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "reddit-sentiment-pipeline.selectorLabels" -}}
app.kubernetes.io/name: {{ include "reddit-sentiment-pipeline.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "reddit-sentiment-pipeline.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "reddit-sentiment-pipeline.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create image name
*/}}
{{- define "reddit-sentiment-pipeline.image" -}}
{{- $registry := .Values.global.imageRegistry | default "" }}
{{- $repository := .Values.image.repository }}
{{- $tag := .Values.image.tag | default .Chart.AppVersion }}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}

{{/*
Create persistent volume claim name
*/}}
{{- define "reddit-sentiment-pipeline.pvcName" -}}
{{- printf "%s-data" (include "reddit-sentiment-pipeline.fullname" .) }}
{{- end }}

{{/*
Create secret name
*/}}
{{- define "reddit-sentiment-pipeline.secretName" -}}
{{- printf "%s-secrets" (include "reddit-sentiment-pipeline.fullname" .) }}
{{- end }}

{{/*
Create configmap name
*/}}
{{- define "reddit-sentiment-pipeline.configMapName" -}}
{{- printf "%s-config" (include "reddit-sentiment-pipeline.fullname" .) }}
{{- end }}
