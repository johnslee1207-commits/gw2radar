# Software Design Document

## 1. System Overview

Two MVP products share one generation engine: AI Export Website Kit Generator and AI Technical Proposal / PDF Report Generator.

## 2. Core Pipeline

Intake -> Knowledge Pack Builder -> Template Renderer -> Generation Provider -> Output Validator -> Export Builder -> Delivery Package

## 3. Main Modules

### Intake Module
Collects structured company, product, market, website goal, technical preference, and package data.

### Knowledge Pack Builder
Normalizes user facts and separates facts from assumptions.

### Template Engine
Loads domain-specific templates for website kits, technical proposals, SEO maps, CMS models, and developer task lists.

### Generation Provider
Abstract interface. MVP includes MockGenerationProvider. Real providers come later.

### Output Validator
Checks required sections, assumption markers, prohibited fabricated claims, and manifest completeness.

### Export Builder
Creates Markdown, CSV, PDF-ready HTML, and package_manifest.json.

## 4. Data Models

Project, Intake, CompanyProfile, ProductProfile, TargetMarket, DeliverableType, KnowledgePack, GeneratedSection, OutputPackage, PackageManifest.

## 5. API Design

POST /projects
GET /projects/{id}
POST /projects/{id}/generate
GET /projects/{id}/outputs
GET /projects/{id}/outputs/{file}

## 6. State Machine

Draft -> IntakeSubmitted -> KnowledgePackReady -> GenerationRunning -> ValidationPending -> ExportReady -> Delivered -> RevisionRequested

## 7. Validation Strategy

Required sections present; minimum content length; assumptions present when facts are missing; prohibited fake claims absent; manifest matches generated files.

## 8. Testing Strategy

Unit tests, integration tests, golden tests, and smoke harness.
