// api/index.ts
import request from '@/utils/request';
import { jobApi } from './jobApi';
import { userApi } from './userApi';

export default request;
export { jobApi, userApi };