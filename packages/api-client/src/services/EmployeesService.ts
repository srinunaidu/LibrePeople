/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Employee } from '../models/Employee';
import type { EmployeeCreate } from '../models/EmployeeCreate';
import type { EmployeeDocument } from '../models/EmployeeDocument';
import type { EmployeeDocumentUpload } from '../models/EmployeeDocumentUpload';
import type { EmployeeHistoryEntry } from '../models/EmployeeHistoryEntry';
import type { EmployeeUpdate } from '../models/EmployeeUpdate';
import type { OrgChartNode } from '../models/OrgChartNode';
import type { PaginatedEmployeeDocuments } from '../models/PaginatedEmployeeDocuments';
import type { PaginatedEmployees } from '../models/PaginatedEmployees';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class EmployeesService {
    /**
     * List employees
     * Lists the employees of this deployment, newest hire first. The list is paged; `page` and `page_size` control the window. Use the filters to narrow it down: `department_id`, `status`, `manager_id` and `search` (matched against the employee number, the name and the email address). Only employees inside the visibility scope of the caller are returned.
     * @returns PaginatedEmployees A page of employees.
     * @throws ApiError
     */
    public static employeesList({
        page = 1,
        pageSize = 50,
        departmentId,
        status,
        managerId,
        locationId,
        search,
        sort,
        order = 'asc',
    }: {
        /**
         * 1-based page number.
         */
        page?: number,
        /**
         * Rows per page. The server may return fewer rows than requested.
         */
        pageSize?: number,
        /**
         * Only employees of this department.
         */
        departmentId?: string,
        /**
         * Only employees in this employment status.
         */
        status?: 'active' | 'on_leave' | 'suspended' | 'terminated',
        /**
         * Only employees reporting to this manager.
         */
        managerId?: string,
        /**
         * Only employees at this location.
         */
        locationId?: string,
        /**
         * Case insensitive match on the employee number, the name and the email address.
         */
        search?: string,
        /**
         * Field to sort on.
         */
        sort?: 'employee_number' | 'last_name' | 'hire_date',
        /**
         * Sort direction.
         */
        order?: 'asc' | 'desc',
    }): CancelablePromise<PaginatedEmployees> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/employees',
            query: {
                'page': page,
                'page_size': pageSize,
                'department_id': departmentId,
                'status': status,
                'manager_id': managerId,
                'location_id': locationId,
                'search': search,
                'sort': sort,
                'order': order,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Create an employee
     * Creates an employee record. The employee number is optional; when it is omitted the deployment allocates the next one. A number that is already taken returns 409 `duplicate_natural_key`. A manager that does not exist, or a reporting line that would close a cycle, returns 422 `validation_error`. Creating an employee never creates a user account; use `POST /auth/users` for that.
     * @returns Employee The employee was created.
     * @throws ApiError
     */
    public static employeesCreate({
        requestBody,
    }: {
        requestBody: EmployeeCreate,
    }): CancelablePromise<Employee> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/employees',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                409: `The request conflicts with the current state of the resource: a duplicate natural key, an illegal state transition, a reused idempotency key, or a concurrent modification. The body carries the \`conflict\` or \`concurrency\` category.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Read the employee record of the caller
     * Returns the employee record that belongs to the authenticated user. A user account without an employee record returns 404 `employee_not_found`; the account itself still works.
     * @returns Employee The employee record of the caller.
     * @throws ApiError
     */
    public static employeesGetMe(): CancelablePromise<Employee> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/employees/me',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Read one employee
     * Returns the employee record. An employee that does not exist, or one that is outside the visibility scope of the caller, returns 404 `employee_not_found`; the endpoint never confirms that a record it refuses to show exists.
     * @returns Employee The employee record.
     * @throws ApiError
     */
    public static employeesGet({
        employeeId,
    }: {
        /**
         * Identifier of the employee.
         */
        employeeId: string,
    }): CancelablePromise<Employee> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/employees/{employee_id}',
            path: {
                'employee_id': employeeId,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Change an employee record
     * Applies a partial change to the employee record. Changes that affect the employment are not written over the current values: they are recorded as effective dated history rows, and the record shows the state at today. A record that was changed by somebody else in the meantime returns 409 `concurrent_update`.
     * @returns Employee The updated employee record.
     * @throws ApiError
     */
    public static employeesUpdate({
        employeeId,
        requestBody,
    }: {
        /**
         * Identifier of the employee.
         */
        employeeId: string,
        requestBody: EmployeeUpdate,
    }): CancelablePromise<Employee> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/employees/{employee_id}',
            path: {
                'employee_id': employeeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                409: `The request conflicts with the current state of the resource: a duplicate natural key, an illegal state transition, a reused idempotency key, or a concurrent modification. The body carries the \`conflict\` or \`concurrency\` category.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * List the documents of an employee
     * Lists the metadata of the documents attached to an employee. The file contents are not returned here; only the metadata needed to identify the document.
     * @returns PaginatedEmployeeDocuments A page of document metadata.
     * @throws ApiError
     */
    public static employeesListDocuments({
        employeeId,
        page = 1,
        pageSize = 50,
        category,
    }: {
        /**
         * Identifier of the employee.
         */
        employeeId: string,
        /**
         * 1-based page number.
         */
        page?: number,
        /**
         * Rows per page. The server may return fewer rows than requested.
         */
        pageSize?: number,
        /**
         * Only documents of this category.
         */
        category?: string,
    }): CancelablePromise<PaginatedEmployeeDocuments> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/employees/{employee_id}/documents',
            path: {
                'employee_id': employeeId,
            },
            query: {
                'page': page,
                'page_size': pageSize,
                'category': category,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Attach a document to an employee
     * Uploads one file and attaches it to the employee. The request is `multipart/form-data`: the `file` part carries the bytes, the other parts carry the metadata. The file is scanned before it is stored; when no scanner is configured for that file type the upload is refused with 503 `malware_scanner_unavailable`. A file that is too large returns 422 `validation_error`. The size limit and the accepted file types are deployment settings and are reported by the configuration assistant.
     * @returns EmployeeDocument The document was stored and attached.
     * @throws ApiError
     */
    public static employeesUploadDocument({
        employeeId,
        formData,
    }: {
        /**
         * Identifier of the employee.
         */
        employeeId: string,
        formData: EmployeeDocumentUpload,
    }): CancelablePromise<EmployeeDocument> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/employees/{employee_id}/documents',
            path: {
                'employee_id': employeeId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Read the employment history of an employee
     * Returns the effective dated changes of the employment record, oldest first. Every row names the field, the previous and the new value, the date the change took effect and the actor that made it. The history is append only: rows are closed with an end date when a newer change supersedes them, they are never edited or deleted.
     * @returns EmployeeHistoryEntry The history rows of the employee.
     * @throws ApiError
     */
    public static employeesGetHistory({
        employeeId,
        from,
        to,
        field,
    }: {
        /**
         * Identifier of the employee.
         */
        employeeId: string,
        /**
         * Only changes effective on or after this date.
         */
        from?: string,
        /**
         * Only changes effective on or before this date.
         */
        to?: string,
        /**
         * Only changes of this field.
         */
        field?: string,
    }): CancelablePromise<Array<EmployeeHistoryEntry>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/employees/{employee_id}/history',
            path: {
                'employee_id': employeeId,
            },
            query: {
                'from': from,
                'to': to,
                'field': field,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Read the reporting tree around an employee
     * Returns the reporting tree that starts at the given employee: the employee, the managers above and the direct reports below. The tree is built from the effective dated manager of each employee, so it reflects the reporting line at today. A cycle in the reporting lines is reported by the configuration assistant and stops the tree from being built.
     * @returns OrgChartNode The reporting tree.
     * @throws ApiError
     */
    public static employeesGetOrgChart({
        employeeId,
        depth = 3,
    }: {
        /**
         * Identifier of the employee the tree starts at.
         */
        employeeId: string,
        /**
         * How many levels to walk up and down.
         */
        depth?: number,
    }): CancelablePromise<OrgChartNode> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/employees/{employee_id}/org-chart',
            path: {
                'employee_id': employeeId,
            },
            query: {
                'depth': depth,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
}
